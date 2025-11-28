# Manual Testing Guide

## Prerequisites

1. Start Docker containers:
   ```bash
   docker compose up -d
   ```

2. Create test users (if needed):
   ```bash
   docker compose exec web python scripts/add_test_users.py
   ```

3. Test user credentials:
   - player1@test.com / test123
   - player2@test.com / test123
   - player3@test.com / test123
   - player4@test.com / test123
   - ... (player5-10)

---

## Test Cases

### Test 1: User Login

**Steps**:
1. Open browser, go to `http://localhost:8000/login`
2. Enter email: `player1@test.com`
3. Enter password: `test123`
4. Click "Login"

**Expected**:
- Login successful
- Redirects to `/home` page
- No errors in console

---

### Test 2: Create Lobby

**Steps**:
1. On `/home` page, click "Create Lobby"

**Expected**:
- Lobby created successfully
- Redirects to `/lobby?code=XXXXXX&lobby_id=Y`
- 6-digit lobby code displayed
- Player list shows player1 (marked as "You")
- Host sees "Start Game" button (disabled if less than 3 players)

---

### Test 3: Join Lobby (Multiple Players)

**Steps**:
1. **Window 1** (player1): Copy the 6-digit lobby code
2. **Window 2** (player2):
   - Go to `http://localhost:8000/login`
   - Login with `player2@test.com` / `test123`
   - On `/home` page, enter lobby code
   - Click "Join Lobby"
3. Repeat for player3 and player4 (use incognito windows or different browsers, 2 browsers and their incognito modes)

**Expected**:
- All players successfully join the lobby
- All windows show all 4 players
- Each window correctly shows own username with "(You)" marker
- Host window shows enabled "Start Game" button (green) when 3+ players

---

### Test 4: Start Game

**Steps**:
1. In host window (player1), click "Start Game" button

**Expected**:
- Game starts successfully
- All 4 windows automatically redirect to `/game?lobby_id=X&game_id=Y&code=XXXXXX`
- Game page displays:
  - Role information (Imposter or Player)
  - Assigned word
  - Timer (50 seconds for Imposter, 30 seconds for others)
  - Clue input field

---

### Test 5: Submit Clues

**Steps**:
1. Each player enters a one-word clue
2. Click "Submit Clue" button
3. Imposter can see other players' clues as they submit

**Expected**:
- Clues submitted successfully
- Imposter sees other players' clues in real-time
- After all players submit, automatically redirects to voting page
- Timer works correctly (30s for regular players, 50s for Imposter)

---

### Test 6: Voting Phase

**Steps**:
1. On voting page, each non-imposter player selects a suspect
2. Click vote button for chosen player
3. Imposter cannot vote (button disabled, message displayed)

**Expected**:
- Votes submitted successfully
- Imposter sees "You are the Imposter! You cannot vote" message
- Vote buttons show each player's clue
- Chat available (anonymous, all players called "Detective")
- After all non-imposter players vote, automatically redirects to results page

---

### Test 7: Voting Timeout

**Steps**:
1. On voting page, wait 30 seconds without voting

**Expected**:
- Timer counts down from 30 to 0
- At 0, displays "Time's up! You didn't vote (abstained)"
- Vote buttons disabled
- Automatically redirects to results page after timeout
- Abstained player gets 0 points (not counted in scoring)

---

### Test 8: Results Page

**Steps**:
1. After voting completes, view results page

**Expected**:
- Displays all votes cast
- Shows total votes per player
- Shows scores per player
- Reveals the Imposter(s)
- Chat available (shows real names, highlights Imposter with 🎭 icon)
- Host sees "Start Next Round" button (if 3+ players remain)

---

### Test 9: Start Next Round

**Steps**:
1. On results page, as host, click "Start Next Round" button

**Expected**:
- New game starts
- All players automatically redirect to new game page
- New words assigned
- New Imposter selected
- Game flow repeats

---

### Test 10: Player Leaves During Game

**Steps**:
1. During clue submission or voting phase, have one player close their browser/tab

**Expected**:
- Other players see alert: "A player has left the lobby. The game has been interrupted."
- All remaining players automatically redirect to lobby page
- Game cannot continue with less than 3 players

---

### Test 11: Player Leaves Before Next Round

**Steps**:
1. On results page, have one player leave the lobby
2. Host tries to start next round

**Expected**:
- Warning message displayed: "Some players have left the lobby..."
- "Start Next Round" button disabled
- Cannot start new round with less than 3 players

---

### Test 12: Scoring System

**Steps**:
1. Complete a full game round
2. Check results page for scores

**Expected**:
- Correct guess → voter gets +1 point
- Wrong guess → Imposter gets +1 point (for each wrong vote)
- Imposter's own vote does not count
- Abstained players get 0 points
- Scores displayed correctly on results page

---

### Test 13: Leaderboard

**Steps**:
1. Complete multiple game rounds
2. On home page, click "View Leaderboard" button
3. Or go directly to `/leaderboard`

**Expected**:
- Global leaderboard displayed
- Shows top players ranked by total score
- Displays username, total score, and games played
- Top 3 players highlighted with 🥇🥈🥉 emojis

---

### Test 14: Chat Functionality

**Steps**:
1. During voting phase, send messages in chat
2. During results phase, send messages in chat

**Expected**:
- Voting phase: Messages displayed anonymously as "Detective: [message]"
- Results phase: Messages show real usernames
- Imposter messages in results phase highlighted in red with 🎭 icon
- Messages appear in real-time (polling every 2 seconds)

