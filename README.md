Imposter Game 

Overview

Imposter Game is a multiplayer web game inspired by social deduction games. Players join a lobby, receive words, and must submit clues to reveal the imposter among them. The game supports multiple rounds, tracks scores, and dynamically updates the lobby as players join.

This milestone focuses on the frontend MVP, with full HTML/CSS/JS implementation and mock backend integration to simulate gameplay while the backend is under development.

Features Implemented (Frontend)
Lobby Creation & Join: Players can create a new lobby or join an existing one using a lobby code.
Lobby Waiting Screen: Displays connected players, lobby code, and enables the host to start the game once 4 players are present.
Game Round Screen: Displays the player’s assigned role and word, allows one-word clue submission, and includes a countdown timer.
Role Types: Normal players, imposter-aware, and imposter-unaware.
Mock API Integration: Uses mock JSON files to simulate backend responses (lobby, player list, assigned word) to enable frontend development independently.
Page Navigation: Home → Lobby → Game Round → Clue Reveal → Voting → Results.
Responsive and Styled UI: Clean HTML/CSS design for MVP.
