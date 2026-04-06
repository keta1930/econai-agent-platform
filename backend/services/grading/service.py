import asyncio
import logging
import mimetypes
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from database import async_session_factory
from models.class_ import Class
from models.model_config import ModelConfig
from models.submission import Submission
from models.task import Task
from services.ai import get_adapter
from services.grading.agents import (
    HighlightResult,
    StandardReviewResult,
    format_learning_resources,
    run_highlight_discoverer,
    run_standard_reviewer,
)
from services.storage import storage_service

logger = logging.getLogger(__name__)


def _build_feedback(
    review: StandardReviewResult | None,
    highlight: HighlightResult | None,
) -> dict:
    """Merge results from both agents into a flat feedback dict."""
    return {
        "dimensions": review.dimensions if review else [],
        "improvements": review.improvements if review else [],
        "overall_comment": review.overall_comment if review else "",
        "highlights": highlight.highlights if highlight else [],
    }


async def grade_submission(submission_id: uuid.UUID) -> None:
    """Background task: grade a submission using dual-agent review."""
    async with async_session_factory() as db:
        try:
            result = await db.execute(
                select(Submission).where(Submission.id == submission_id)
            )
            submission = result.scalar_one_or_none()
            if not submission:
                logger.error("Submission %s not found", submission_id)
                return

            submission.status = "grading"
            await db.commit()

            # Query chain: Task -> Class -> ModelConfig
            result = await db.execute(
                select(Task).where(Task.id == submission.task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                logger.error(
                    "Task %s not found for submission %s",
                    submission.task_id,
                    submission_id,
                )
                submission.status = "failed"
                await db.commit()
                return

            result = await db.execute(
                select(Class).where(Class.id == task.class_id)
            )
            cls = result.scalar_one_or_none()
            if not cls:
                logger.error("Class %s not found for task %s", task.class_id, task.id)
                submission.status = "failed"
                await db.commit()
                return

            result = await db.execute(
                select(ModelConfig).where(
                    ModelConfig.admin_id == cls.created_by,
                    ModelConfig.is_active == True,  # noqa: E712
                )
            )
            model_config = result.scalar_one_or_none()
            if not model_config:
                logger.error("No active model for admin %s", cls.created_by)
                submission.status = "failed"
                await db.commit()
                return

            adapter = get_adapter(model_config)
            context: dict = {
                "task_description": task.description or "",
                "grading_criteria": task.grading_criteria or "",
                "learning_resources": format_learning_resources(
                    task.learning_resources
                ),
            }

            file_paths: list[str] = submission.file_path  # JSON array

            if submission.content_type == "image":
                # VLM capability check
                if not model_config.supports_vision:
                    logger.info(
                        "Model %s does not support vision, marking submission %s as manual_review",
                        model_config.name,
                        submission_id,
                    )
                    submission.status = "manual_review"
                    await db.commit()
                    return

                # Read all images from storage
                images: list[tuple[bytes, str]] = []
                total_size = 0
                for path in file_paths:
                    img_bytes = await asyncio.to_thread(
                        storage_service.get_object, path,
                    )
                    mime, _ = mimetypes.guess_type(path)
                    images.append((img_bytes, mime or "image/jpeg"))
                    total_size += len(img_bytes)

                logger.info(
                    "Submission %s: %d images, total %.1f MB",
                    submission_id,
                    len(images),
                    total_size / (1024 * 1024),
                )
                context["images"] = images
                context["submission_content"] = ""
            else:
                # Text / file: read content as string (file_path is a JSON array, take first)
                content = await asyncio.to_thread(
                    storage_service.get_text, file_paths[0],
                )
                context["submission_content"] = content

            # Run both agents in parallel
            results = await asyncio.gather(
                run_standard_reviewer(adapter, context),
                run_highlight_discoverer(adapter, context),
                return_exceptions=True,
            )

            review_result = results[0]
            highlight_result = results[1]

            review_ok = isinstance(review_result, StandardReviewResult)
            highlight_ok = isinstance(highlight_result, HighlightResult)

            if not review_ok and not highlight_ok:
                # Both agents failed
                logger.error(
                    "Both agents failed for submission %s: reviewer=%s, highlighter=%s",
                    submission_id,
                    review_result,
                    highlight_result,
                )
                submission.status = "failed"
                await db.commit()
                return

            review = review_result if review_ok else None
            highlight = highlight_result if highlight_ok else None

            if not review_ok:
                logger.warning(
                    "Standard reviewer failed for submission %s: %s",
                    submission_id,
                    review_result,
                )

            if not highlight_ok:
                logger.warning(
                    "Highlight discoverer failed for submission %s: %s",
                    submission_id,
                    highlight_result,
                )

            # Final score: max of available scores
            scores = []
            if review:
                scores.append(review.score)
            if highlight:
                scores.append(highlight.score)
            final_score = max(scores)

            submission.score = final_score
            submission.feedback = _build_feedback(review, highlight)
            submission.status = "completed"
            submission.graded_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(
                "Submission %s graded: score=%s (reviewer=%s, highlighter=%s)",
                submission_id,
                final_score,
                review.score if review else "FAILED",
                highlight.score if highlight else "FAILED",
            )

        except Exception:
            logger.exception("Grading failed for submission %s", submission_id)
            try:
                if "submission" in locals() and submission is not None:
                    submission.status = "failed"
                    await db.commit()
            except Exception:
                logger.exception("Failed to update submission status to failed")
