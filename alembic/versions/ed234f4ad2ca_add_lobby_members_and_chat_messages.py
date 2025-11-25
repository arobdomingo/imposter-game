"""add_lobby_members_and_chat_messages

Revision ID: ed234f4ad2ca
Revises: 9207d5a8a27f
Create Date: 2025-11-23 05:47:08.600913

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ed234f4ad2ca"
down_revision: Union[str, Sequence[str], None] = "9207d5a8a27f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create lobby_members table
    op.create_table(
        "lobby_members",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "lobby_id",
            sa.Integer(),
            sa.ForeignKey("lobbies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seat_no", sa.Integer(), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("lobby_id", "user_id", name="uq_lobby_members_lobby_user"),
    )
    op.create_index(
        op.f("ix_lobby_members_lobby_id"), "lobby_members", ["lobby_id"], unique=False
    )
    op.create_index(
        op.f("ix_lobby_members_user_id"), "lobby_members", ["user_id"], unique=False
    )

    # Create chat_messages table
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "game_id",
            sa.Integer(),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column(
            "message_type",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'text'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        op.f("ix_chat_messages_game_id"), "chat_messages", ["game_id"], unique=False
    )
    op.create_index(
        op.f("ix_chat_messages_user_id"), "chat_messages", ["user_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop chat_messages table
    op.drop_index(op.f("ix_chat_messages_user_id"), table_name="chat_messages")
    op.drop_index(op.f("ix_chat_messages_game_id"), table_name="chat_messages")
    op.drop_table("chat_messages")

    # Drop lobby_members table
    op.drop_index(op.f("ix_lobby_members_user_id"), table_name="lobby_members")
    op.drop_index(op.f("ix_lobby_members_lobby_id"), table_name="lobby_members")
    op.drop_table("lobby_members")
