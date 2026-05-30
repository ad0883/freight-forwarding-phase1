"""s3_subscription_foundation

Revision ID: 3390b79c6d15
Revises: phase24_enterprise_govern
Create Date: 2026-05-30 16:14:10.266818
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3390b79c6d15'
down_revision: Union[str, None] = 'phase24_enterprise_govern'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # subscription_plans
    op.create_table(
        'subscription_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_key', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('billing_period', sa.String(length=50), nullable=False, server_default='monthly'),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='USD'),
        sa.Column('base_price_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('trial_days_default', sa.Integer(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscription_plans_id'), 'subscription_plans', ['id'], unique=False)
    op.create_index(op.f('ix_subscription_plans_plan_key'), 'subscription_plans', ['plan_key'], unique=True)

    # subscription_plan_features
    op.create_table(
        'subscription_plan_features',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('feature_key', sa.String(length=100), nullable=False),
        sa.Column('feature_label', sa.String(length=255), nullable=False),
        sa.Column('feature_description', sa.Text(), nullable=True),
        sa.Column('included', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('limit_value', sa.Integer(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscription_plan_features_id'), 'subscription_plan_features', ['id'], unique=False)

    # organization_subscriptions
    op.create_table(
        'organization_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('subscription_status', sa.String(length=50), nullable=False, server_default='trial'),
        sa.Column('billing_mode', sa.String(length=50), nullable=False, server_default='manual'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('trial_started_at', sa.DateTime(), nullable=True),
        sa.Column('trial_ends_at', sa.DateTime(), nullable=True),
        sa.Column('current_period_start', sa.DateTime(), nullable=True),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('suspended_at', sa.DateTime(), nullable=True),
        sa.Column('reactivated_at', sa.DateTime(), nullable=True),
        sa.Column('manual_payment_reference', sa.String(length=255), nullable=True),
        sa.Column('billing_contact_name', sa.String(length=255), nullable=True),
        sa.Column('billing_contact_email', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_by_name', sa.String(length=255), nullable=True),
        sa.Column('updated_by_user_id', sa.Integer(), nullable=True),
        sa.Column('updated_by_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id')
    )
    op.create_index(op.f('ix_organization_subscriptions_id'), 'organization_subscriptions', ['id'], unique=False)

    # subscription_events
    op.create_table(
        'subscription_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('safe_summary', sa.Text(), nullable=False),
        sa.Column('old_status', sa.String(length=50), nullable=True),
        sa.Column('new_status', sa.String(length=50), nullable=True),
        sa.Column('old_plan_key', sa.String(length=100), nullable=True),
        sa.Column('new_plan_key', sa.String(length=100), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_by_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['subscription_id'], ['organization_subscriptions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscription_events_id'), 'subscription_events', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_subscription_events_id'), table_name='subscription_events')
    op.drop_table('subscription_events')
    op.drop_index(op.f('ix_organization_subscriptions_id'), table_name='organization_subscriptions')
    op.drop_table('organization_subscriptions')
    op.drop_index(op.f('ix_subscription_plan_features_id'), table_name='subscription_plan_features')
    op.drop_table('subscription_plan_features')
    op.drop_index(op.f('ix_subscription_plans_plan_key'), table_name='subscription_plans')
    op.drop_index(op.f('ix_subscription_plans_id'), table_name='subscription_plans')
    op.drop_table('subscription_plans')

