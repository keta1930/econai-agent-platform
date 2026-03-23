import logging
from datetime import datetime
from pathlib import Path

from database import SessionLocal
from models.submission import Submission
from models.task import Task
from models.model_config import ModelConfig
from services.ai.base import BaseAIAdapter
from config import STORAGE_DIR

logger = logging.getLogger(__name__)

GRADING_PROMPT_TEMPLATE = """你是一位严格的作业批改助手。请根据以下打分标准对学生作业进行评分。

## 打分标准
{grading_criteria}

## 学生作业
{submission_content}

## 输出要求
请以 JSON 格式输出，包含两个字段：
- score: 数字，表示分数
- suggestion: 字符串，表示改进建议

仅输出 JSON，不要输出其他内容。"""


def get_adapter(model_config: ModelConfig) -> BaseAIAdapter:
    if model_config.adapter_type == "openai":
        from services.ai.openai_adapter import OpenAIAdapter
        return OpenAIAdapter(
            api_key=model_config.api_key,
            base_url=model_config.base_url,
            model_name=model_config.name,
        )
    elif model_config.adapter_type == "anthropic":
        from services.ai.anthropic_adapter import AnthropicAdapter
        return AnthropicAdapter(
            api_key=model_config.api_key,
            base_url=model_config.base_url,
            model_name=model_config.name,
        )
    else:
        raise ValueError(f"Unknown adapter type: {model_config.adapter_type}")


def grade_submission(submission_id: int):
    """Background task: grade a submission using the active AI model."""
    db = SessionLocal()
    try:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            logger.error("Submission %d not found", submission_id)
            return

        # Update status to grading
        submission.status = "grading"
        db.commit()

        # Get active model config
        model_config = db.query(ModelConfig).filter(ModelConfig.is_active == True).first()
        if not model_config:
            logger.error("No active model configured")
            submission.status = "failed"
            db.commit()
            return

        # Read submission file
        file_path = Path(STORAGE_DIR) / submission.file_path
        if not file_path.exists():
            logger.error("Submission file not found: %s", file_path)
            submission.status = "failed"
            db.commit()
            return

        content = file_path.read_text(encoding="utf-8")

        # Get task grading criteria
        task = db.query(Task).filter(Task.id == submission.task_id).first()
        if not task:
            logger.error("Task %d not found for submission %d", submission.task_id, submission_id)
            submission.status = "failed"
            db.commit()
            return

        # Call AI
        adapter = get_adapter(model_config)
        result = adapter.grade(content, task.grading_criteria)

        # Save result
        submission.score = result.score
        submission.suggestion = result.suggestion
        submission.status = "completed"
        submission.graded_at = datetime.utcnow()
        db.commit()

        logger.info("Submission %d graded: score=%s", submission_id, result.score)

    except Exception:
        logger.exception("Grading failed for submission %d", submission_id)
        try:
            submission.status = "failed"
            db.commit()
        except Exception:
            logger.exception("Failed to update submission status to failed")
    finally:
        db.close()
