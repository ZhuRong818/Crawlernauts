"""Add job_id to CrawlResult

Revision ID: 6b9ebf50fbd2
Revises: 
Create Date: 2025-07-17 14:17:34.375691
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6b9ebf50fbd2'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('crawl_result', schema=None) as batch_op:
        batch_op.add_column(sa.Column('job_id', sa.Integer()))
        batch_op.create_foreign_key(
            constraint_name='fk_crawlresult_job_id',
            referent_table='crawl_job',
            local_cols=['job_id'],
            remote_cols=['id']
        )


def downgrade():
    with op.batch_alter_table('crawl_result', schema=None) as batch_op:
        batch_op.drop_constraint('fk_crawlresult_job_id', type_='foreignkey')
        batch_op.drop_column('job_id')
