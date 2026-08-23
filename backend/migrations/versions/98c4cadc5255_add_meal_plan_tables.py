from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '98c4cadc5255'
down_revision = 'f18e00b797e8'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('meal_plans',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('plan_date', sa.Date(), nullable=False),
    sa.Column('plan_type', sa.String(), nullable=True),
    sa.Column('is_ai_generated', sa.Boolean(), nullable=True),
    sa.Column('safety_validated', sa.Boolean(), nullable=True),
    sa.Column('targets_snapshot', sa.JSON(), nullable=True),
    sa.Column('gap_report', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_meal_plans_user_id'), 'meal_plans', ['user_id'], unique=False)
    
    op.create_table('meal_plan_meals',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('plan_id', sa.UUID(), nullable=False),
    sa.Column('meal_type', sa.String(), nullable=False),
    sa.Column('day_number', sa.Integer(), nullable=True),
    sa.Column('foods', sa.JSON(), nullable=False),
    sa.Column('total_nutrition', sa.JSON(), nullable=True),
    sa.Column('rationale', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['plan_id'], ['meal_plans.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('meal_plan_meals')
    op.drop_index(op.f('ix_meal_plans_user_id'), table_name='meal_plans')
    op.drop_table('meal_plans')
