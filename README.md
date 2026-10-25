# Imposter Game

A multiplayer social-deduction game developed by a **five-person team** for **CMPT 276 — Introduction to Software Engineering** at Simon Fraser University. Players join lobbies, receive roles, submit clues, vote and compete across rounds.

## Features
- User accounts, JWT authentication and Discord OAuth.
- Multiplayer lobbies, role assignment, clues, voting, scoring and leaderboards.
- WebSocket support for real-time gameplay updates.
- PostgreSQL persistence, SQLAlchemy and Alembic migrations.
- Event and analytics services, admin functionality and automated tests.

## Stack
Python, FastAPI, WebSockets, PostgreSQL, SQLAlchemy, Alembic, HTML/CSS/JavaScript, Docker Compose, pytest.

## Explore
- [Gameplay demo](demo.mp4)
- [Testing checklist](TESTING_CHECKLIST.md)
- `src/game_service/` — game and lobby logic.
- `src/user_service/` — user and authentication logic.
- `frontend/` — browser interface.
- `alembic/` — database migrations.

## Local setup
Requires Python 3.13+, Docker and Docker Compose. Configure the database and Discord OAuth environment variables referenced by `docker-compose.yml`, then:

```bash
docker compose up --build
```

Tests can be run in a configured environment with `pytest`. Some features require additional service configuration.

## Security
**Review the tracked `private.pem` file before deploying or sharing this repository.** Never use a committed private key as a live credential; rotate any exposed active key and remove sensitive material from history as appropriate.

## Credits
Collaborative academic project. Features described here reflect the team repository, not necessarily one individual's contributions.
