# migrations/versions/initial_migration.py
"""initial migration

Revision ID: initial
Revises: 
Create Date: 2024-12-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('content',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('ARTICLE', 'REDDIT', 'TWEET', name='contenttype'), nullable=False),
        sa.Column('url', sa.String(length=512), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('scraped_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_type_scraped_at', 'content', ['type', 'scraped_at'])
    op.create_index(op.f('ix_content_scraped_at'), 'content', ['scraped_at'])

def downgrade():
    op.drop_index(op.f('ix_content_scraped_at'), table_name='content')
    op.drop_index('idx_type_scraped_at', table_name='content')
    op.drop_table('content')