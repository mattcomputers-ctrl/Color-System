"""Add tolerance profiles, substrate-series associations, and ink_type column.

Revision ID: 002_tolerance_associations
Revises: 001_add_substrates
Create Date: 2026-03-13
"""
from alembic import op
import sqlalchemy as sa

revision = '002_tolerance_associations'
down_revision = '001_add_substrates'
branch_labels = None
depends_on = None


def upgrade():
    # Tolerance profiles table
    op.create_table(
        'tolerance_profiles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('customer_name', sa.String(200), nullable=True),
        sa.Column('de_excellent', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('de_good', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('de_acceptable', sa.Float(), nullable=False, server_default='2.0'),
        sa.Column('de76_acceptable', sa.Float(), nullable=True, server_default='3.0'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    )

    # Substrate-series association table
    op.create_table(
        'substrate_series_associations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('series_id', sa.Integer(), sa.ForeignKey('ink_series.id'), nullable=False),
        sa.Column('substrate_id', sa.Integer(), sa.ForeignKey('substrates.id'), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('series_id', 'substrate_id', name='uq_series_substrate'),
    )

    # Add ink_type to ink_series
    op.add_column('ink_series', sa.Column('ink_type', sa.String(50), server_default='litho'))


def downgrade():
    op.drop_column('ink_series', 'ink_type')
    op.drop_table('substrate_series_associations')
    op.drop_table('tolerance_profiles')
