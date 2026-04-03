"""multitenancy baseline

Revision ID: 0001_multitenancy
Revises:
Create Date: 2026-04-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_multitenancy"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users must be created before classes (classes.created_by -> users.id)
    # but classes must exist before users.class_id FK can reference it.
    # Solution: create users first without the class_id FK, then classes, then add the FK.

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.CheckConstraint(
            "role IN ('super_admin', 'admin', 'student')",
            name="ck_users_role",
        ),
        sa.UniqueConstraint("username", "class_id", name="uq_user_username_class"),
    )

    op.create_table(
        "classes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_classes")),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"],
            name=op.f("fk_classes_created_by_users"),
        ),
        sa.UniqueConstraint("name", "created_by", name="uq_class_name_admin"),
    )

    # Now add the FK from users.class_id -> classes.id
    op.create_foreign_key(
        op.f("fk_users_class_id_classes"),
        "users", "classes",
        ["class_id"], ["id"],
    )

    op.create_table(
        "student_roster",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_roster")),
        sa.ForeignKeyConstraint(
            ["class_id"], ["classes.id"],
            name=op.f("fk_student_roster_class_id_classes"),
        ),
        sa.UniqueConstraint("student_id", "class_id", name="uq_roster_student_class"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("grading_criteria", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
        sa.ForeignKeyConstraint(
            ["class_id"], ["classes.id"],
            name=op.f("fk_tasks_class_id_classes"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"],
            name=op.f("fk_tasks_created_by_users"),
        ),
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_submissions")),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"],
            name=op.f("fk_submissions_task_id_tasks"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"],
            name=op.f("fk_submissions_student_id_users"),
        ),
        sa.UniqueConstraint(
            "task_id", "student_id", "version",
            name="uq_submission_task_student_version",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'grading', 'completed', 'failed')",
            name="ck_submissions_status",
        ),
    )

    op.create_table(
        "model_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("api_key", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=False),
        sa.Column("adapter_type", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_configs")),
        sa.ForeignKeyConstraint(
            ["admin_id"], ["users.id"],
            name=op.f("fk_model_configs_admin_id_users"),
        ),
        sa.UniqueConstraint("name", "admin_id", name="uq_model_name_admin"),
        sa.CheckConstraint(
            "adapter_type IN ('openai', 'anthropic')",
            name="ck_model_configs_adapter_type",
        ),
    )

    op.create_table(
        "sharing_topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="voting"),
        sa.Column("presenters", sa.String(), nullable=True),
        sa.Column("session_number", sa.Integer(), nullable=True),
        sa.Column("shared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("materials_content", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("submitted_by", sa.Integer(), nullable=True),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sharing_topics")),
        sa.ForeignKeyConstraint(
            ["submitted_by"], ["users.id"],
            name=op.f("fk_sharing_topics_submitted_by_users"),
        ),
        sa.ForeignKeyConstraint(
            ["class_id"], ["classes.id"],
            name=op.f("fk_sharing_topics_class_id_classes"),
        ),
    )

    op.create_table(
        "topic_votes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topic_votes")),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["sharing_topics.id"],
            name=op.f("fk_topic_votes_topic_id_sharing_topics"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"],
            name=op.f("fk_topic_votes_student_id_users"),
        ),
        sa.UniqueConstraint("topic_id", "student_id", name="uq_vote_topic_student"),
    )


def downgrade() -> None:
    op.drop_table("topic_votes")
    op.drop_table("sharing_topics")
    op.drop_table("model_configs")
    op.drop_table("submissions")
    op.drop_table("tasks")
    op.drop_table("student_roster")
    op.drop_constraint(op.f("fk_users_class_id_classes"), "users", type_="foreignkey")
    op.drop_table("classes")
    op.drop_table("users")
