"""add_sector_model

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 检查表是否已存在（可能通过 Base.metadata.create_all() 自动创建）
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    table_exists = 'sectors' in inspector.get_table_names()
    
    if not table_exists:
        # 创建 sectors 表
        op.create_table(
            'sectors',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False, comment='板块名称，如 沪深A股、深市ETF'),
            sa.Column('display_name', sa.String(length=100), nullable=True, comment='显示名称，用于前端展示'),
            sa.Column('category', sa.String(length=50), nullable=True, comment='板块分类：股票、基金、债券、期货、期权、指数等'),
            sa.Column('market', sa.String(length=10), nullable=True, comment='所属市场：SH、SZ、BJ等，None表示跨市场'),
            sa.Column('description', sa.Text(), nullable=True, comment='板块描述'),
            sa.Column('security_count', sa.Integer(), nullable=True, server_default='0', comment='板块内证券数量'),
            sa.Column('is_active', sa.Integer(), nullable=True, server_default='1', comment='是否有效，1-有效，0-无效'),
            sa.Column('last_sync_at', sa.DateTime(), nullable=True, comment='最后同步时间'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), comment='创建时间'),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), comment='更新时间'),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 检查并创建索引（使用唯一前缀避免与其他表的索引冲突）
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('sectors')] if table_exists else []
    
    if 'idx_sectors_name' not in existing_indexes:
        op.create_index('idx_sectors_name', 'sectors', ['name'], unique=True, if_not_exists=True)
    if 'idx_sectors_category' not in existing_indexes:
        op.create_index('idx_sectors_category', 'sectors', ['category'], if_not_exists=True)
    if 'idx_sectors_market' not in existing_indexes:
        op.create_index('idx_sectors_market', 'sectors', ['market'], if_not_exists=True)
    if 'idx_sectors_is_active' not in existing_indexes:
        op.create_index('idx_sectors_is_active', 'sectors', ['is_active'], if_not_exists=True)


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_sectors_is_active', table_name='sectors')
    op.drop_index('idx_sectors_market', table_name='sectors')
    op.drop_index('idx_sectors_category', table_name='sectors')
    op.drop_index('idx_sectors_name', table_name='sectors')
    
    # 删除表
    op.drop_table('sectors')

