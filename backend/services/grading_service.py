import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from database import async_session_factory
from models.submission import Submission
from models.task import Task
from models.class_ import Class
from models.model_config import ModelConfig
from services.ai import get_adapter
from services.storage import storage_service

logger = logging.getLogger(__name__)


async def grade_submission(submission_id: uuid.UUID):
    """Background task: grade a submission using the active AI model."""
    async with async_session_factory() as db:
        try:
            result = await db.execute(
                select(Submission).where(Submission.id == submission_id)
            )
            submission = result.scalar_one_or_none()
            if not submission:
                logger.error("Submission %s not found", submission_id)
                return

            # Image submissions skip AI grading (status already set to manual_review)
            if submission.content_type == "image":
                # TODO: enable vision grading here via adapter.grade_image()
                return

            # Update status to grading
            submission.status = "grading"
            await db.commit()

            # Get task to find class -> admin
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

            # Find admin via class
            result = await db.execute(
                select(Class).where(Class.id == task.class_id)
            )
            cls = result.scalar_one_or_none()
            if not cls:
                logger.error("Class %s not found for task %s", task.class_id, task.id)
                submission.status = "failed"
                await db.commit()
                return

            # Get active model config for admin
            result = await db.execute(
                select(ModelConfig).where(
                    ModelConfig.admin_id == cls.created_by,
                    ModelConfig.is_active == True,
                )
            )
            model_config = result.scalar_one_or_none()
            if not model_config:
                logger.error("No active model for admin %s", cls.created_by)
                submission.status = "failed"
                await db.commit()
                return

            # Read submission file from MinIO
            content = await asyncio.to_thread(
                storage_service.get_text, submission.file_path
            )

            # Call AI
            adapter = get_adapter(model_config)
            result = await asyncio.to_thread(
                adapter.grade, content, task.grading_criteria, task.description
            )

            # Save result
            submission.score = result.score
            submission.suggestion = result.suggestion
            submission.status = "completed"
            submission.graded_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(
                "Submission %s graded: score=%s", submission_id, result.score
            )

        except Exception:
            logger.exception("Grading failed for submission %s", submission_id)
            try:
                if "submission" in locals() and submission is not None:
                    submission.status = "failed"
                    await db.commit()
            except Exception:
                logger.exception("Failed to update submission status to failed")
