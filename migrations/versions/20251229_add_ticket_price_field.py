"""Add price field to Ticket model

Revision ID: a1b2c3d4e5f6
Revises: 0188b85f78ae
Create Date: 2025-12-29 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '0188b85f78ae'
branch_labels = None
depends_on = None


def upgrade():
    # Check if tables exist before modifying
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Only add price column if ticket table exists and doesn't have it
    if 'ticket' in tables:
        columns = [col['name'] for col in inspector.get_columns('ticket')]

        if 'price' not in columns:
            # Add price column with nullable=True initially
            op.add_column('ticket', sa.Column('price', sa.Integer(), nullable=True))

            # Backfill existing tickets with current SHARPENING_PRICE_DKK (80)
            op.execute("UPDATE ticket SET price = 80 WHERE price IS NULL")

            # Make column non-nullable after backfill
            with op.batch_alter_table('ticket') as batch_op:
                batch_op.alter_column('price', nullable=False)


def downgrade():
    # Remove price column from ticket table
    with op.batch_alter_table('ticket') as batch_op:
        batch_op.drop_column('price')
