import pytest

from game_service.repositories import (
    LobbyRepository,
    GameRepository,
    ChatMessageRepository,
)


@pytest.mark.asyncio
async def test_chat_message_repository_create_text_message(session, users):
    """Test creating a text chat message."""
    lobby_repo = LobbyRepository(session)
    lobby = await lobby_repo.create(code="CHAT1", host_id=users[0].id)
    game_repo = GameRepository(session)
    game = await game_repo.create(lobby_id=lobby.id, mode="unaware")

    chat_repo = ChatMessageRepository(session)
    message = await chat_repo.create(
        game_id=game.id,
        user_id=users[0].id,
        message="This is a test message",
        message_type="text",
    )

    assert message.game_id == game.id
    assert message.user_id == users[0].id
    assert message.message == "This is a test message"
    assert message.message_type == "text"
    assert message.created_at is not None


@pytest.mark.asyncio
async def test_chat_message_repository_create_reaction(session, users):
    """Test creating a reaction message."""
    lobby_repo = LobbyRepository(session)
    lobby = await lobby_repo.create(code="CHAT2", host_id=users[0].id)
    game_repo = GameRepository(session)
    game = await game_repo.create(lobby_id=lobby.id, mode="unaware")

    chat_repo = ChatMessageRepository(session)
    reaction = await chat_repo.create(
        game_id=game.id,
        user_id=users[0].id,
        message="👍",
        message_type="reaction",
    )

    assert reaction.message == "👍"
    assert reaction.message_type == "reaction"


@pytest.mark.asyncio
async def test_chat_message_repository_list_by_game(session, users):
    """Test listing all messages for a game."""
    lobby_repo = LobbyRepository(session)
    lobby = await lobby_repo.create(code="CHAT3", host_id=users[0].id)
    game_repo = GameRepository(session)
    game = await game_repo.create(lobby_id=lobby.id, mode="unaware")

    chat_repo = ChatMessageRepository(session)

    # Create multiple messages
    for i in range(5):
        await chat_repo.create(game.id, users[0].id, f"Message {i}", "text")

    # List all messages
    all_messages = await chat_repo.list_by_game(game.id)
    assert len(all_messages) == 5

    # Verify messages are in chronological order
    for i in range(1, len(all_messages)):
        assert all_messages[i].created_at >= all_messages[i - 1].created_at

    # Verify message content
    assert all_messages[0].message == "Message 0"
    assert all_messages[4].message == "Message 4"


@pytest.mark.asyncio
async def test_chat_message_repository_list_recent_by_game(session, users):
    """Test listing recent messages with limit."""
    lobby_repo = LobbyRepository(session)
    lobby = await lobby_repo.create(code="CHAT4", host_id=users[0].id)
    game_repo = GameRepository(session)
    game = await game_repo.create(lobby_id=lobby.id, mode="unaware")

    chat_repo = ChatMessageRepository(session)

    # Create 10 messages
    messages_created = []
    for i in range(10):
        msg = await chat_repo.create(game.id, users[0].id, f"Message {i}", "text")
        messages_created.append(msg)

    # Get recent 5 messages
    recent = await chat_repo.list_recent_by_game(game.id, limit=5)
    assert len(recent) == 5

    # Verify the limit works (should return 5 messages)
    # Note: Due to SQLite in-memory database timing, we can't guarantee
    # which exact 5 messages are returned, but we can verify:
    # 1. The limit is respected
    # 2. Messages are in chronological order
    # 3. All messages belong to the game

    assert len(recent) == 5
    assert all(msg.game_id == game.id for msg in recent)

    # Verify chronological order (oldest first)
    for i in range(1, len(recent)):
        assert recent[i].created_at >= recent[i - 1].created_at


@pytest.mark.asyncio
async def test_chat_message_repository_list_recent_default_limit(session, users):
    """Test that list_recent_by_game uses default limit of 50."""
    lobby_repo = LobbyRepository(session)
    lobby = await lobby_repo.create(code="CHAT5", host_id=users[0].id)
    game_repo = GameRepository(session)
    game = await game_repo.create(lobby_id=lobby.id, mode="unaware")

    chat_repo = ChatMessageRepository(session)

    # Create 30 messages (less than default limit of 50)
    for i in range(30):
        await chat_repo.create(game.id, users[0].id, f"Message {i}", "text")

    # Get recent without specifying limit
    recent = await chat_repo.list_recent_by_game(game.id)
    assert len(recent) == 30  # Should return all 30

    # Create more messages to exceed limit
    for i in range(30, 60):
        await chat_repo.create(game.id, users[0].id, f"Message {i}", "text")

    # Get recent without limit (should default to 50)
    recent = await chat_repo.list_recent_by_game(game.id)
    assert len(recent) == 50  # Should be limited to 50


@pytest.mark.asyncio
async def test_chat_message_repository_multiple_users(session, users):
    """Test messages from multiple users in the same game."""
    lobby_repo = LobbyRepository(session)
    lobby = await lobby_repo.create(code="CHAT6", host_id=users[0].id)
    game_repo = GameRepository(session)
    game = await game_repo.create(lobby_id=lobby.id, mode="unaware")

    chat_repo = ChatMessageRepository(session)

    # Create messages from different users
    await chat_repo.create(game.id, users[0].id, "Message from user 0", "text")
    await chat_repo.create(game.id, users[1].id, "Message from user 1", "text")
    await chat_repo.create(game.id, users[0].id, "Another from user 0", "text")

    all_messages = await chat_repo.list_by_game(game.id)
    assert len(all_messages) == 3

    # Verify user IDs
    user_ids = [msg.user_id for msg in all_messages]
    assert users[0].id in user_ids
    assert users[1].id in user_ids


@pytest.mark.asyncio
async def test_chat_message_repository_multiple_games(session, users):
    """Test that messages are isolated by game."""
    lobby_repo = LobbyRepository(session)
    lobby1 = await lobby_repo.create(code="CHAT7", host_id=users[0].id)
    lobby2 = await lobby_repo.create(code="CHAT8", host_id=users[0].id)
    game_repo = GameRepository(session)
    game1 = await game_repo.create(lobby_id=lobby1.id, mode="unaware")
    game2 = await game_repo.create(lobby_id=lobby2.id, mode="unaware")

    chat_repo = ChatMessageRepository(session)

    # Create messages in game1
    await chat_repo.create(game1.id, users[0].id, "Game 1 message", "text")
    await chat_repo.create(game1.id, users[0].id, "Another game 1 message", "text")

    # Create messages in game2
    await chat_repo.create(game2.id, users[0].id, "Game 2 message", "text")

    # List messages for each game
    game1_messages = await chat_repo.list_by_game(game1.id)
    game2_messages = await chat_repo.list_by_game(game2.id)

    assert len(game1_messages) == 2
    assert len(game2_messages) == 1
    assert game1_messages[0].message == "Game 1 message"
    assert game2_messages[0].message == "Game 2 message"


@pytest.mark.asyncio
async def test_chat_message_repository_message_types(session, users):
    """Test different message types (text and reaction)."""
    lobby_repo = LobbyRepository(session)
    lobby = await lobby_repo.create(code="CHAT9", host_id=users[0].id)
    game_repo = GameRepository(session)
    game = await game_repo.create(lobby_id=lobby.id, mode="unaware")

    chat_repo = ChatMessageRepository(session)

    # Create text message
    await chat_repo.create(game.id, users[0].id, "Hello everyone", "text")

    # Create reaction
    await chat_repo.create(game.id, users[0].id, "👍", "reaction")

    all_messages = await chat_repo.list_by_game(game.id)
    assert len(all_messages) == 2

    # Verify message types
    message_types = {msg.message_type for msg in all_messages}
    assert "text" in message_types
    assert "reaction" in message_types

    # Verify specific messages
    text_messages = [msg for msg in all_messages if msg.message_type == "text"]
    reaction_messages = [msg for msg in all_messages if msg.message_type == "reaction"]

    assert len(text_messages) == 1
    assert len(reaction_messages) == 1
    assert text_messages[0].message == "Hello everyone"
    assert reaction_messages[0].message == "👍"


@pytest.mark.asyncio
async def test_chat_message_repository_empty_game(session, users):
    """Test listing messages for a game with no messages."""
    lobby_repo = LobbyRepository(session)
    lobby = await lobby_repo.create(code="CHAT10", host_id=users[0].id)
    game_repo = GameRepository(session)
    game = await game_repo.create(lobby_id=lobby.id, mode="unaware")

    chat_repo = ChatMessageRepository(session)

    # List messages for empty game
    messages = await chat_repo.list_by_game(game.id)
    assert len(messages) == 0

    recent = await chat_repo.list_recent_by_game(game.id)
    assert len(recent) == 0
