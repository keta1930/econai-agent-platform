"""baseline — create all core tables

Revision ID: 0000000000
Revises:
Create Date: 2026-04-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0000000000'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- invite_codes (no dependencies) ---
    op.create_table(
        'invite_codes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('code_hash', sa.String(), nullable=False),
        sa.Column('code_prefix', sa.String(length=8), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_invite_codes')),
        sa.UniqueConstraint('code_hash', name=op.f('uq_invite_codes_code_hash')),
    )
    op.create_index(op.f('ix_invite_codes_code_prefix'), 'invite_codes', ['code_prefix'], unique=False)

    # --- users (depends on invite_codes) ---
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('password_change_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('invite_code_id', sa.Uuid(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("role IN ('super_admin', 'admin', 'student')", name='ck_users_role'),
        sa.CheckConstraint('password_change_count >= 0 AND password_change_count <= 3', name='ck_users_password_change_count'),
        sa.ForeignKeyConstraint(['invite_code_id'], ['invite_codes.id'], name=op.f('fk_users_invite_code_id_invite_codes'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    )
    op.create_index(
        'uq_student_username', 'users', ['username'],
        unique=True,
        postgresql_where=sa.text("role = 'student'"),
    )
    op.create_index(
        'uq_admin_username', 'users', ['username'],
        unique=True,
        postgresql_where=sa.text("role IN ('admin', 'super_admin')"),
    )

    # --- classes (depends on users) ---
    op.create_table(
        'classes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=False),
        sa.Column('join_token', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_classes_created_by_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_classes')),
        sa.UniqueConstraint('join_token', name=op.f('uq_classes_join_token')),
        sa.UniqueConstraint('name', 'created_by', name='uq_class_name_admin'),
    )

    # --- refresh_tokens (depends on users) ---
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('class_id', sa.Uuid(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_refresh_tokens_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens')),
        sa.UniqueConstraint('token_hash', name=op.f('uq_refresh_tokens_token_hash')),
    )
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)

    # --- backups (depends on users) ---
    op.create_table(
        'backups',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('admin_id', sa.Uuid(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('object_key', sa.String(), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id'], name=op.f('fk_backups_admin_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_backups')),
        sa.UniqueConstraint('object_key', name=op.f('uq_backups_object_key')),
    )

    # --- model_configs (depends on users) ---
    op.create_table(
        'model_configs',
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
        sa.UniqueConstraint('name', 'admin_id', name='uq_model_name_admin'),
    )

    # --- class_members (depends on users, classes) ---
    op.create_table(
        'class_members',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('class_id', sa.Uuid(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], name=op.f('fk_class_members_class_id_classes'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_class_members_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_class_members')),
        sa.UniqueConstraint('user_id', 'class_id', name='uq_class_member'),
    )

    # --- student_roster (depends on classes) ---
    op.create_table(
        'student_roster',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('student_id', sa.String(), nullable=False),
        sa.Column('class_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], name=op.f('fk_student_roster_class_id_classes')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_student_roster')),
        sa.UniqueConstraint('student_id', 'class_id', name='uq_roster_student_class'),
    )

    # --- tasks (depends on classes, users) ---
    op.create_table(
        'tasks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('grading_criteria', sa.Text(), nullable=False),
        sa.Column('learning_resources', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('class_id', sa.Uuid(), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], name=op.f('fk_tasks_class_id_classes')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_tasks_created_by_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_tasks')),
    )

    # --- submissions (depends on tasks, users) ---
    op.create_table(
        'submissions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('student_id', sa.Uuid(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), server_default='file', nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('feedback', sa.JSON(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('graded_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("content_type IN ('text', 'file', 'image')", name='ck_submissions_content_type'),
        sa.CheckConstraint("status IN ('pending', 'grading', 'completed', 'failed', 'manual_review')", name='ck_submissions_status'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], name=op.f('fk_submissions_student_id_users')),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name=op.f('fk_submissions_task_id_tasks')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_submissions')),
        sa.UniqueConstraint('task_id', 'student_id', 'version', name='uq_submission_task_student_version'),
    )

    # --- sharing_topics (depends on users, classes) ---
    op.create_table(
        'sharing_topics',
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
        sa.PrimaryKeyConstraint('id', name=op.f('pk_sharing_topics')),
    )

    # --- topic_votes (depends on sharing_topics, users) ---
    op.create_table(
        'topic_votes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('topic_id', sa.Uuid(), nullable=False),
        sa.Column('student_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], name=op.f('fk_topic_votes_student_id_users')),
        sa.ForeignKeyConstraint(['topic_id'], ['sharing_topics.id'], name=op.f('fk_topic_votes_topic_id_sharing_topics')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_topic_votes')),
        sa.UniqueConstraint('topic_id', 'student_id', name='uq_vote_topic_student'),
    )


def downgrade() -> None:
    op.drop_table('topic_votes')
    op.drop_table('sharing_topics')
    op.drop_table('submissions')
    op.drop_table('tasks')
    op.drop_table('student_roster')
    op.drop_table('class_members')
    op.drop_table('model_configs')
    op.drop_table('backups')
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_table('classes')
    op.drop_index('uq_admin_username', table_name='users')
    op.drop_index('uq_student_username', table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_invite_codes_code_prefix'), table_name='invite_codes')
    op.drop_table('invite_codes')
