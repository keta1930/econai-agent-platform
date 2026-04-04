"""0001_uuid_baseline

Revision ID: d726466edb2f
Revises:
Create Date: 2026-04-04 02:13:26.953639

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd726466edb2f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- Phase 1: create tables with circular FK deferred ---
    # classes: created WITHOUT FK to users (added later)
    op.create_table('classes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_classes')),
    sa.UniqueConstraint('name', 'created_by', name='uq_class_name_admin')
    )

    # users: created WITH FK to classes (classes already exists)
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('class_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("role IN ('super_admin', 'admin', 'student')", name='ck_users_role'),
    sa.ForeignKeyConstraint(['class_id'], ['classes.id'], name=op.f('fk_users_class_id_classes')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('username', 'class_id', name='uq_user_username_class')
    )

    # --- Phase 2: add deferred FK from classes.created_by -> users.id ---
    op.create_foreign_key(
        op.f('fk_classes_created_by_users'),
        'classes', 'users',
        ['created_by'], ['id'],
    )

    # --- Phase 3: remaining tables (no circular deps) ---
    op.create_table('backups',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('admin_id', sa.Uuid(), nullable=False),
    sa.Column('display_name', sa.String(), nullable=False),
    sa.Column('object_key', sa.String(), nullable=False),
    sa.Column('size', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['admin_id'], ['users.id'], name=op.f('fk_backups_admin_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_backups')),
    sa.UniqueConstraint('object_key', name=op.f('uq_backups_object_key'))
    )
    op.create_table('model_configs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('api_key', sa.String(), nullable=False),
    sa.Column('base_url', sa.String(), nullable=False),
    sa.Column('adapter_type', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('admin_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("adapter_type IN ('openai', 'anthropic')", name='ck_model_configs_adapter_type'),
    sa.ForeignKeyConstraint(['admin_id'], ['users.id'], name=op.f('fk_model_configs_admin_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_model_configs')),
    sa.UniqueConstraint('name', 'admin_id', name='uq_model_name_admin')
    )
    op.create_table('sharing_topics',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('presenters', sa.String(), nullable=True),
    sa.Column('session_number', sa.Integer(), nullable=True),
    sa.Column('shared_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('materials_content', sa.Text(), nullable=True),
    sa.Column('display_order', sa.Integer(), nullable=False),
    sa.Column('submitted_by', sa.Uuid(), nullable=True),
    sa.Column('class_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['class_id'], ['classes.id'], name=op.f('fk_sharing_topics_class_id_classes')),
    sa.ForeignKeyConstraint(['submitted_by'], ['users.id'], name=op.f('fk_sharing_topics_submitted_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sharing_topics'))
    )
    op.create_table('student_roster',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('student_id', sa.String(), nullable=False),
    sa.Column('class_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['class_id'], ['classes.id'], name=op.f('fk_student_roster_class_id_classes')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_student_roster')),
    sa.UniqueConstraint('student_id', 'class_id', name='uq_roster_student_class')
    )
    op.create_table('tasks',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('grading_criteria', sa.Text(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('class_id', sa.Uuid(), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['class_id'], ['classes.id'], name=op.f('fk_tasks_class_id_classes')),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_tasks_created_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tasks'))
    )
    op.create_table('submissions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('task_id', sa.Uuid(), nullable=False),
    sa.Column('student_id', sa.Uuid(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('file_path', sa.String(), nullable=False),
    sa.Column('content_type', sa.String(), server_default='file', nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('score', sa.Float(), nullable=True),
    sa.Column('suggestion', sa.Text(), nullable=True),
    sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('graded_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("content_type IN ('text', 'file', 'image')", name='ck_submissions_content_type'),
    sa.CheckConstraint("status IN ('pending', 'grading', 'completed', 'failed', 'manual_review')", name='ck_submissions_status'),
    sa.ForeignKeyConstraint(['student_id'], ['users.id'], name=op.f('fk_submissions_student_id_users')),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name=op.f('fk_submissions_task_id_tasks')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_submissions')),
    sa.UniqueConstraint('task_id', 'student_id', 'version', name='uq_submission_task_student_version')
    )
    op.create_table('topic_votes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('topic_id', sa.Uuid(), nullable=False),
    sa.Column('student_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['student_id'], ['users.id'], name=op.f('fk_topic_votes_student_id_users')),
    sa.ForeignKeyConstraint(['topic_id'], ['sharing_topics.id'], name=op.f('fk_topic_votes_topic_id_sharing_topics')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_topic_votes')),
    sa.UniqueConstraint('topic_id', 'student_id', name='uq_vote_topic_student')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('topic_votes')
    op.drop_table('submissions')
    op.drop_table('tasks')
    op.drop_table('student_roster')
    op.drop_table('sharing_topics')
    op.drop_table('model_configs')
    op.drop_table('backups')
    op.drop_constraint(op.f('fk_classes_created_by_users'), 'classes', type_='foreignkey')
    op.drop_table('users')
    op.drop_table('classes')
