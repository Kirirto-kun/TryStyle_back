"""Add user roles and store admin system

Revision ID: 55c8f6013452
Revises: f35e6348eb3c
Create Date: 2025-07-10 23:04:26.599602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '55c8f6013452'
down_revision: Union[str, None] = 'f35e6348eb3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Создаем ENUM тип для ролей пользователей
    user_role_enum = postgresql.ENUM('USER', 'STORE_ADMIN', 'ADMIN', name='userrole')
    user_role_enum.create(op.get_bind())
    
    # Добавляем колонку role со значением по умолчанию
    op.add_column('users', sa.Column('role', user_role_enum, nullable=True))
    
    # Устанавливаем значение по умолчанию для существующих записей
    op.execute("UPDATE users SET role = 'USER' WHERE role IS NULL")
    
    # Теперь делаем колонку NOT NULL
    op.alter_column('users', 'role', nullable=False)
    
    # Добавляем колонку store_id
    op.add_column('users', sa.Column('store_id', sa.Integer(), nullable=True))
    
    # Создаем индексы
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_index(op.f('ix_users_store_id'), 'users', ['store_id'], unique=False)
    
    # Создаем foreign key constraint
    op.create_foreign_key('fk_users_store_id', 'users', 'stores', ['store_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем foreign key constraint
    op.drop_constraint('fk_users_store_id', 'users', type_='foreignkey')
    
    # Удаляем индексы
    op.drop_index(op.f('ix_users_store_id'), table_name='users')
    op.drop_index(op.f('ix_users_role'), table_name='users')
    
    # Удаляем колонки
    op.drop_column('users', 'store_id')
    op.drop_column('users', 'role')
    
    # Удаляем ENUM тип
    op.execute('DROP TYPE userrole')
