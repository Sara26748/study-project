"""Added funktional column to requirement

Revision ID: 09473f86f396
Revises: 
Create Date: 2026-01-08 15:58:17.939270

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '09473f86f396'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Nur die neue Spalte zur Tabelle 'requirement' hinzufügen
    with op.batch_alter_table('requirement', schema=None) as batch_op:
        batch_op.add_column(sa.Column('funktional', sa.Boolean(), nullable=True))


def downgrade():
    # Nur die neue Spalte aus der Tabelle 'requirement' entfernen
    with op.batch_alter_table('requirement', schema=None) as batch_op:
        batch_op.drop_column('funktional')
