"""Add SMS delivery status fields to Ticket

Revision ID: b7e2c9f41d3a
Revises: 6a57427d97ed
Create Date: 2026-11-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7e2c9f41d3a'
down_revision = '6a57427d97ed'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ticket', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sms_status', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('sms_error', sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table('ticket', schema=None) as batch_op:
        batch_op.drop_column('sms_error')
        batch_op.drop_column('sms_status')
