"""initial schema: links and clicks

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "links",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("is_custom_alias", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("click_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_links_code"), "links", ["code"], unique=True)
    op.create_index(op.f("ix_links_is_active"), "links", ["is_active"], unique=False)
    op.create_index("ix_links_active_created", "links", ["is_active", "created_at"], unique=False)

    op.create_table(
        "clicks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("link_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("referrer", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("device_type", sa.String(length=32), nullable=True),
        sa.Column("browser", sa.String(length=64), nullable=True),
        sa.Column("os", sa.String(length=64), nullable=True),
        sa.Column("country", sa.String(length=80), nullable=True),
        sa.Column("country_code", sa.String(length=8), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["link_id"], ["links.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clicks_link_id"), "clicks", ["link_id"], unique=False)
    op.create_index(op.f("ix_clicks_created_at"), "clicks", ["created_at"], unique=False)
    op.create_index("ix_clicks_link_created", "clicks", ["link_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_clicks_link_created", table_name="clicks")
    op.drop_index(op.f("ix_clicks_created_at"), table_name="clicks")
    op.drop_index(op.f("ix_clicks_link_id"), table_name="clicks")
    op.drop_table("clicks")
    op.drop_index("ix_links_active_created", table_name="links")
    op.drop_index(op.f("ix_links_is_active"), table_name="links")
    op.drop_index(op.f("ix_links_code"), table_name="links")
    op.drop_table("links")
