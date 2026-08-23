"""unique_constraint_condition_name_medication_name

Revision ID: ec1dd30679ea
Revises: 98c4cadc5255
Create Date: 2026-08-23 11:45:53.947814

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec1dd30679ea'
down_revision: Union[str, None] = '98c4cadc5255'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('conditions') as batch_op:
        batch_op.create_unique_constraint('uq_condition_name', ['name'])
        
    with op.batch_alter_table('medications') as batch_op:
        batch_op.create_unique_constraint('uq_medication_name', ['generic_name'])


def downgrade() -> None:
    with op.batch_alter_table('medications') as batch_op:
        batch_op.drop_constraint('uq_medication_name', type_='unique')
        
    with op.batch_alter_table('conditions') as batch_op:
        batch_op.drop_constraint('uq_condition_name', type_='unique')
