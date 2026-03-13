"""Add substrates table.

Revision ID: 001_add_substrates
Revises: None
Create Date: 2026-03-13
"""
from alembic import op
import sqlalchemy as sa

revision = '001_add_substrates'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'substrates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('substrate_type', sa.String(100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('spectral_reflectance', sa.JSON(), nullable=True),
        sa.Column('wavelength_start', sa.Integer(), server_default='360'),
        sa.Column('wavelength_end', sa.Integer(), server_default='780'),
        sa.Column('wavelength_interval', sa.Integer(), server_default='10'),
        sa.Column('ks_values', sa.JSON(), nullable=True),
        sa.Column('lab_l', sa.Float(), nullable=True),
        sa.Column('lab_a', sa.Float(), nullable=True),
        sa.Column('lab_b', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('uploaded_file_id', sa.Integer(), sa.ForeignKey('uploaded_files.id'), nullable=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_substrates_code', 'substrates', ['code'], unique=True)


def downgrade():
    op.drop_index('ix_substrates_code', table_name='substrates')
    op.drop_table('substrates')
