"""Baseline: the contact_submission table as it existed before migrations were added.

Databases created earlier by db.create_all() already have this table, so it is only
created when missing. That lets `flask db upgrade` run on both old and fresh databases.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-07
"""
import sqlalchemy as sa
from alembic import op

revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    if 'contact_submission' in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        'contact_submission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('phone', sa.String(length=30), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('contact_submission')
