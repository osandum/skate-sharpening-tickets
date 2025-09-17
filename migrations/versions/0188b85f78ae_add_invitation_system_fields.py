"""Add invitation system fields

Revision ID: 0188b85f78ae
Revises: 
Create Date: 2025-09-17 08:49:23.251854

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0188b85f78ae'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Check if tables exist before modifying
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Only add columns if sharpener table exists and doesn't have them
    if 'sharpener' in tables:
        columns = [col['name'] for col in inspector.get_columns('sharpener')]

        if 'email' not in columns:
            op.add_column('sharpener', sa.Column('email', sa.String(255), nullable=True))
            # Update existing rows to have a placeholder email
            op.execute("UPDATE sharpener SET email = name || '@example.com' WHERE email IS NULL")

        if 'is_active' not in columns:
            op.add_column('sharpener', sa.Column('is_active', sa.Boolean(), nullable=True))
            # Set all existing users as active
            op.execute("UPDATE sharpener SET is_active = 1 WHERE is_active IS NULL")

    # Create invitation table if it doesn't exist
    if 'invitation' not in tables:
        op.create_table('invitation',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(255), nullable=False),
            sa.Column('token', sa.String(100), nullable=False),
            sa.Column('used', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('email'),
            sa.UniqueConstraint('token')
        )


def downgrade():
    # Drop invitation table
    op.drop_table('invitation')

    # Remove columns from sharpener table
    with op.batch_alter_table('sharpener') as batch_op:
        batch_op.drop_column('is_active')
        batch_op.drop_column('email')
