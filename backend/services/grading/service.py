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
    """合并两个 Agent 的结果为扁平反馈字典。"""
    return {
        "dimensions": review.dimensions if review else [],
        "improvements": review.improvements if review else [],
        "overall_comment": review.overall_comment if review else "",
        "highlights": highlight.highlights if highlight else [],
    }


async def grade_submission(submission_id: uuid.UUID) -> None:
    """后台任务：使用双 Agent 批改提交。"""
    async with async_session_factory() as db:
        try:
            result = await db.execute(
                select(Submission).where(Submission.id == submission_id)
            )
            submission = result.scalar_one_or_none()
            if not submission:
                logger.error("提交不存在 — id=%s", submission_id)
                return

            submission.status = "grading"
            await db.commit()

            logger.info("批改开始 — 提交=%s, 类型=%s", submission_id, submission.content_type)

            # 查询链：Task -> Class -> ModelConfig
            result = await db.execute(
                select(Task).where(Task.id == submission.task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                logger.error(
                    "作业不存在 — 作业=%s, 提交=%s",
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
                logger.error("班级不存在 — 班级=%s, 作业=%s", task.class_id, task.id)
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
                logger.error("无可用模型 — 管理员=%s", cls.created_by)
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

            file_paths: list[str] = submission.file_path  # JSON 数组

            if submission.content_type == "image":
                # 视觉能力检查
                if not model_config.supports_vision:
                    logger.info(
                        "模型不支持视觉 — 模型=%s, 提交=%s, 转为人工批改",
                        model_config.name,
                        submission_id,
                    )
                    submission.status = "manual_review"
                    await db.commit()
                    return

                # 从存储读取所有图片
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
                    "图片读取完成 — 提交=%s, 数量=%d, 总大小=%.1fMB",
                    submission_id,
                    len(images),
                    total_size / (1024 * 1024),
                )
                context["images"] = images
                context["submission_content"] = ""
            else:
                # 文本/文件：读取内容字符串（file_path 是 JSON 数组，取第一个）
                content = await asyncio.to_thread(
                    storage_service.get_text, file_paths[0],
                )
                context["submission_content"] = content

            # 并行运行两个 Agent
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
                # 两个 Agent 都失败
                logger.error(
                    "双 Agent 均失败 — 提交=%s, 评审=%s, 亮点=%s",
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
                    "标准评审 Agent 失败 — 提交=%s, 错误=%s",
                    submission_id,
                    review_result,
                )

            if not highlight_ok:
                logger.warning(
                    "亮点发现 Agent 失败 — 提交=%s, 错误=%s",
                    submission_id,
                    highlight_result,
                )

            # 最终得分：取可用分数的最大值
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
                "批改完成 — 提交=%s, 得分=%.1f (评审=%s, 亮点=%s)",
                submission_id,
                final_score,
                review.score if review else "失败",
                highlight.score if highlight else "失败",
            )

        except Exception:
            logger.exception("批改异常 — 提交=%s", submission_id)
            try:
                if "submission" in locals() and submission is not None:
                    submission.status = "failed"
                    await db.commit()
            except Exception:
                logger.exception("更新提交状态为 failed 时出错")
