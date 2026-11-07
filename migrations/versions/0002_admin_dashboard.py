"""Admin dashboard: enquiry status/service fields, activity timeline, AI widget log.

Revision ID: 0002_admin_dashboard
Revises: 0001_baseline
Create Date: 2026-11-07
"""
import sqlalchemy as sa
from alembic import op

revision = '0002_admin_dashboard'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('contact_submission') as batch:
        batch.add_column(sa.Column('service', sa.String(length=30), nullable=True))
        batch.add_column(sa.Column('preferred_contact', sa.String(length=20), nullable=True))
        batch.add_column(sa.Column('consent', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch.add_column(sa.Column('status', sa.String(length=20), server_default='new', nullable=False))
        batch.add_column(sa.Column('contacted_at', sa.DateTime(), nullable=True))
        batch.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
        batch.create_index('ix_contact_submission_status', ['status'])
        batch.create_index('ix_contact_submission_submitted_at', ['submitted_at'])

    op.create_table(
        'activity',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('from_status', sa.String(length=20), nullable=True),
        sa.Column('to_status', sa.String(length=20), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('author', sa.String(length=80), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['submission_id'], ['contact_submission.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_activity_submission_id', 'activity', ['submission_id'])

    op.create_table(
        'service_fit_query',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('suggested', sa.String(length=60), nullable=True),
        sa.Column('ok', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_service_fit_query_created_at', 'service_fit_query', ['created_at'])


def downgrade():
    op.drop_index('ix_service_fit_query_created_at', table_name='service_fit_query')
    op.drop_table('service_fit_query')
    op.drop_index('ix_activity_submission_id', table_name='activity')
    op.drop_table('activity')
    with op.batch_alter_table('contact_submission') as batch:
        batch.drop_index('ix_contact_submission_submitted_at')
        batch.drop_index('ix_contact_submission_status')
        for col in ('updated_at', 'contacted_at', 'status', 'consent', 'preferred_contact', 'service'):
            batch.drop_column(col)
