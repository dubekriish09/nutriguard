from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f18e00b797e8'
down_revision = '1efabd3beb36'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('foods', sa.Column('glycemic_index', sa.Integer(), nullable=True))
    op.add_column('foods', sa.Column('purine_level', sa.String(), nullable=True))
    op.add_column('foods', sa.Column('vitamin_k_mcg', sa.Numeric(), nullable=True))
    op.add_column('foods', sa.Column('nutrient_source', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('foods', 'nutrient_source')
    op.drop_column('foods', 'vitamin_k_mcg')
    op.drop_column('foods', 'purine_level')
    op.drop_column('foods', 'glycemic_index')
