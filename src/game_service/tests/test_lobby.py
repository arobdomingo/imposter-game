import pytest
from sqlalchemy.exc import IntegrityError

from game_service.repositories import (
    LobbyRepository,
    LobbyMemberRepository,
    GameRepository,
)
from game_service.services.lobby_service import LobbyService
from game_service.services.game_engine import GameEngine
from game_service.services.word_service import WordService


@pytest.mark.asyncio
async def test_lobby_member_repository_add_and_remove(session, users):
    """Test adding and removing lobby members."""
    lobby_repo = LobbyRepository(session)
    lobby = await lobby_repo.create(code="TEST1", host_id=users[0].id)

    member_repo = LobbyMemberRepository(session)

    # Add first member
    member1 = await member_repo.add_member(lobby.id, users[0].id, seat_no=1)
    assert member1.lobby_id == lobby.id
    assert member1.user_id == users[0].id
    assert member1.seat_no == 1

    # Add second member
    member2 = await member_repo.add_member(lobby.id, users[1].id, seat_no=2)
    assert member2.user_id == users[1].id

    # List all members
    members = await member_repo.list_members(lobby.id)
    assert len(members) == 2
    assert {m.user_id for m in members} == {users[0].id, users[1].id}

    # Count members
    count = await member_repo.count_members(lobby.id)
    assert count == 2

    # Remove a member
    removed = await member_repo.remove_member(lobby.id, users[1].id)
    assert removed is True

    members_after = await member_repo.list_members(lobby.id)
    assert len(members_after) == 1
    assert members_after[0].user_id == users[0].id


@pytest.mark.asyncio
async def test_lobby_member_repository_unique_constraint(session, users):
    """Test that a user cannot join the same lobby twice."""
    lobby_repo = LobbyRepository(session)
    lobby = await lobby_repo.create(code="TEST2", host_id=users[0].id)

    member_repo = LobbyMemberRepository(session)
    await member_repo.add_member(lobby.id, users[0].id, seat_no=1)

    # Try to add the same user again
    with pytest.raises(IntegrityError):
        await member_repo.add_member(lobby.id, users[0].id, seat_no=2)
    session.rollback()


@pytest.mark.asyncio
async def test_lobby_member_repository_get_member(session, users):
    """Test getting a specific member."""
    lobby_repo = LobbyRepository(session)
    lobby = await lobby_repo.create(code="TEST3", host_id=users[0].id)

    member_repo = LobbyMemberRepository(session)
    await member_repo.add_member(lobby.id, users[0].id, seat_no=1)

    member = await member_repo.get_member(lobby.id, users[0].id)
    assert member is not None
    assert member.user_id == users[0].id

    # Non-existent member
    non_existent = await member_repo.get_member(lobby.id, users[1].id)
    assert non_existent is None


@pytest.mark.asyncio
async def test_lobby_service_create_lobby(session, users):
    """Test creating a lobby with LobbyService."""
    lobby_repo = LobbyRepository(session)
    member_repo = LobbyMemberRepository(session)
    game_repo = GameRepository(session)

    # Create a mock game engine
    from game_service.repositories import (
        PlayerRepository,
        ClueRepository,
        VoteRepository,
    )
    from game_service.services.game_engine import GameEngine

    # We'll need to create a simple engine for testing
    # For now, let's use a minimal setup
    word_service = WordService()
    game_engine = GameEngine(
        lobby_repo=lobby_repo,
        game_repo=game_repo,
        player_repo=PlayerRepository(session),
        clue_repo=ClueRepository(session),
        vote_repo=VoteRepository(session),
        word_service=word_service,
    )

    lobby_service = LobbyService(
        lobby_repo=lobby_repo,
        lobby_member_repo=member_repo,
        game_repo=game_repo,
        game_engine=game_engine,
    )

    lobby_id, code = await lobby_service.create_lobby(users[0].id)

    assert lobby_id is not None
    assert len(code) == 6  # CODE_LENGTH = 6

    # Verify lobby was created
    lobby = await lobby_repo.get_by_id(lobby_id)
    assert lobby is not None
    assert lobby.host_id == users[0].id
    assert lobby.code == code

    # Verify host was added as member
    members = await member_repo.list_members(lobby_id)
    assert len(members) == 1
    assert members[0].user_id == users[0].id
    assert members[0].seat_no == 1


@pytest.mark.asyncio
async def test_lobby_service_join_lobby(session, users):
    """Test joining a lobby."""
    lobby_repo = LobbyRepository(session)
    member_repo = LobbyMemberRepository(session)
    game_repo = GameRepository(session)

    from game_service.repositories import (
        PlayerRepository,
        ClueRepository,
        VoteRepository,
    )

    word_service = WordService()
    game_engine = GameEngine(
        lobby_repo=lobby_repo,
        game_repo=game_repo,
        player_repo=PlayerRepository(session),
        clue_repo=ClueRepository(session),
        vote_repo=VoteRepository(session),
        word_service=word_service,
    )

    lobby_service = LobbyService(
        lobby_repo=lobby_repo,
        lobby_member_repo=member_repo,
        game_repo=game_repo,
        game_engine=game_engine,
    )

    # Create lobby
    lobby_id, _ = await lobby_service.create_lobby(users[0].id)

    # Join with second user
    success = await lobby_service.join_lobby(lobby_id, users[1].id)
    assert success is True

    members = await member_repo.list_members(lobby_id)
    assert len(members) == 2
    user_ids = {m.user_id for m in members}
    assert user_ids == {users[0].id, users[1].id}


@pytest.mark.asyncio
async def test_lobby_service_join_full_lobby(session, users):
    """Test that joining a full lobby fails."""
    lobby_repo = LobbyRepository(session)
    member_repo = LobbyMemberRepository(session)
    game_repo = GameRepository(session)

    from game_service.repositories import (
        PlayerRepository,
        ClueRepository,
        VoteRepository,
    )

    word_service = WordService()
    game_engine = GameEngine(
        lobby_repo=lobby_repo,
        game_repo=game_repo,
        player_repo=PlayerRepository(session),
        clue_repo=ClueRepository(session),
        vote_repo=VoteRepository(session),
        word_service=word_service,
    )

    lobby_service = LobbyService(
        lobby_repo=lobby_repo,
        lobby_member_repo=member_repo,
        game_repo=game_repo,
        game_engine=game_engine,
    )

    # Create lobby
    lobby_id, _ = await lobby_service.create_lobby(users[0].id)

    # Fill lobby to max capacity (4 players)
    for i in range(1, 4):
        await lobby_service.join_lobby(lobby_id, users[i].id)

    # Try to join when full
    success = await lobby_service.join_lobby(
        lobby_id, users[3].id if len(users) > 3 else users[0].id
    )
    # Should fail or return False (depending on implementation)
    # Actually, if we try to add users[0] again, it should return True (already a member)
    # Let's test with a new user
    if len(users) >= 5:
        success = await lobby_service.join_lobby(lobby_id, users[4].id)
        assert success is False


@pytest.mark.asyncio
async def test_lobby_service_manual_start_game(session, users):
    """Test that game does NOT auto-start when lobby is full. Host must manually start."""
    lobby_repo = LobbyRepository(session)
    member_repo = LobbyMemberRepository(session)
    game_repo = GameRepository(session)

    from game_service.repositories import (
        PlayerRepository,
        ClueRepository,
        VoteRepository,
    )

    word_service = WordService()
    game_engine = GameEngine(
        lobby_repo=lobby_repo,
        game_repo=game_repo,
        player_repo=PlayerRepository(session),
        clue_repo=ClueRepository(session),
        vote_repo=VoteRepository(session),
        word_service=word_service,
    )

    lobby_service = LobbyService(
        lobby_repo=lobby_repo,
        lobby_member_repo=member_repo,
        game_repo=game_repo,
        game_engine=game_engine,
    )

    # Create lobby
    lobby_id, _ = await lobby_service.create_lobby(users[0].id)

    # Add players until full (4 players total)
    for i in range(1, min(4, len(users))):
        await lobby_service.join_lobby(lobby_id, users[i].id)

    # Check that game was NOT automatically created
    game = await game_repo.get_active_by_lobby(lobby_id)
    if len(users) >= 4:
        # Game should NOT be created when 4th player joins
        assert game is None, "Game should not be created automatically"

    # Host manually starts the game
    if len(users) >= 4:
        members = await member_repo.list_members(lobby_id)
        user_ids = [
            member.user_id for member in sorted(members, key=lambda m: m.seat_no or 0)
        ]
        game_id = await game_engine.start_game(lobby_id, user_ids, mode="aware")

        # Verify game was created after manual start
        game = await game_repo.get_active_by_lobby(lobby_id)
        assert game is not None
        assert game.lobby_id == lobby_id
        assert game.id == game_id
        assert game.status == "waiting"  # Game starts in waiting status
        assert game.mode == "aware"


@pytest.mark.asyncio
async def test_lobby_service_leave_lobby(session, users):
    """Test leaving a lobby."""
    lobby_repo = LobbyRepository(session)
    member_repo = LobbyMemberRepository(session)
    game_repo = GameRepository(session)

    from game_service.repositories import (
        PlayerRepository,
        ClueRepository,
        VoteRepository,
    )

    word_service = WordService()
    game_engine = GameEngine(
        lobby_repo=lobby_repo,
        game_repo=game_repo,
        player_repo=PlayerRepository(session),
        clue_repo=ClueRepository(session),
        vote_repo=VoteRepository(session),
        word_service=word_service,
    )

    lobby_service = LobbyService(
        lobby_repo=lobby_repo,
        lobby_member_repo=member_repo,
        game_repo=game_repo,
        game_engine=game_engine,
    )

    # Create lobby and add members
    lobby_id, _ = await lobby_service.create_lobby(users[0].id)
    await lobby_service.join_lobby(lobby_id, users[1].id)

    # Leave lobby
    success = await lobby_service.leave_lobby(lobby_id, users[1].id)
    assert success is True

    members = await member_repo.list_members(lobby_id)
    assert len(members) == 1
    assert members[0].user_id == users[0].id


@pytest.mark.asyncio
async def test_lobby_service_generate_unique_code(session, users):
    """Test that generated codes are unique."""
    lobby_repo = LobbyRepository(session)
    member_repo = LobbyMemberRepository(session)
    game_repo = GameRepository(session)

    from game_service.repositories import (
        PlayerRepository,
        ClueRepository,
        VoteRepository,
    )

    word_service = WordService()
    game_engine = GameEngine(
        lobby_repo=lobby_repo,
        game_repo=game_repo,
        player_repo=PlayerRepository(session),
        clue_repo=ClueRepository(session),
        vote_repo=VoteRepository(session),
        word_service=word_service,
    )

    lobby_service = LobbyService(
        lobby_repo=lobby_repo,
        lobby_member_repo=member_repo,
        game_repo=game_repo,
        game_engine=game_engine,
    )

    # Generate multiple codes
    codes = set()
    for _ in range(10):
        code = await lobby_service.generate_unique_code()
        assert len(code) == 6
        assert code not in codes
        codes.add(code)
