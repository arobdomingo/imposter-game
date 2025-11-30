// Wait for API to load
document.addEventListener('DOMContentLoaded', () => {
  // Load API script if not already loaded
  if (!window.API) {
    const script = document.createElement('script');
    script.src = '/js/api.js';
    document.head.appendChild(script);
    script.onload = initVotePage;
  } else {
    initVotePage();
  }
});

function initVotePage() {
  // Check authentication
  if (!requireAuth()) {
    return; // Redirect to login if not authenticated
  }
  
  // Get game info from URL
  const params = new URLSearchParams(window.location.search);
  const gameId = parseInt(params.get("game_id"));
  const lobbyId = parseInt(params.get("lobby_id"));
  const lobbyCode = params.get("code") || "";

  if (!gameId) {
    alert("Game ID not found. Refreshing page...");
    window.location.reload();
    return;
  }

  // Get current user ID
  const currentUserId = window.API.getCurrentUserId();
  if (!currentUserId) {
    alert("Please login first!");
    window.location.href = "/login";
    return;
  }

  // Game state
  let gameState = {
    gameId: gameId,
    lobbyId: lobbyId,
    currentUserId: currentUserId,
    myPlayerId: null,
    isImposter: false,
    players: [],
    myVote: null,
    allVotesSubmitted: false,
    mySeatNo: null,
    currentRound: 1, // Default to round 1
    clues: {}, // { player_id: clue_word }
    originalPlayerCount: 0,
    playerCheckInterval: null,
    hasAbstained: false, // Track if current player abstained (timeout)
    timeoutHandled: false // Track if timeout has been handled
  };

  // Elements
  const playerTurnEl = document.getElementById('playerTurn');
  const suspectOptionsEl = document.getElementById('suspectOptions');
  const voteTimerEl = document.getElementById('voteTimer');
  const voteStatusEl = document.getElementById('voteStatus');
  const quirkyLineEl = document.getElementById('quirkyLine');
  const chatBoxEl = document.getElementById('chatBox');
  const chatInputEl = document.getElementById('chatInput');
  const chatSendBtnEl = document.getElementById('chatSendBtn');

  // Timer
  let timeLeft = 30;
  let timer = null;
  let voteStartTime = null; // Track when voting started

  // ----- Initialize voting page -----
  async function initVoting() {
    try {
      // Get player's role
      const roleData = await window.API.Lobby.getRole(gameId, currentUserId);
      gameState.myPlayerId = roleData.player_id;
      gameState.isImposter = roleData.is_imposter || false;
      gameState.mySeatNo = roleData.seat_no || 1;

      // Get game info to get players
      const gameData = await window.API.Lobby.getGame(lobbyId);
      if (gameData && gameData.players) {
        gameState.players = gameData.players;
        
        // Fetch user names for each player (silently handle 404s)
        const playerPromises = gameData.players.map(async (player) => {
          try {
            const user = await window.API.User.getById(player.user_id);
            return {
              ...player,
              user_name: user ? user.name : null
            };
          } catch (err) {
            // User not found (404) - silently use fallback name
            // Don't log 404 errors to console
            if (err.status === 404 || (err.message && err.message.includes("User not found"))) {
              return {
                ...player,
                user_name: `Player ${player.seat_no || player.id}`
              };
            }
            // For other errors, log but still return fallback
            console.warn(`Error fetching user ${player.user_id}:`, err.message);
            return {
              ...player,
              user_name: `Player ${player.seat_no || player.id}`
            };
          }
        });
        
        // Use Promise.allSettled to handle errors gracefully
        const results = await Promise.allSettled(playerPromises);
        gameState.players = results.map((result, index) => {
          if (result.status === 'fulfilled') {
            return result.value;
          } else {
            // If promise rejected, use fallback
            const player = gameData.players[index];
            return {
              ...player,
              user_name: `Player ${player.seat_no || player.id}`
            };
          }
        });
      }

      // Load clues for current round (round 1 for first voting phase)
      await loadCluesForRound(gameState.currentRound);

      // Check if Imposter
      if (gameState.isImposter) {
        // Imposter cannot vote
        playerTurnEl.textContent = "You are the Imposter!";
        playerTurnEl.style.color = "#d32f2f";
        playerTurnEl.style.fontWeight = "bold";
        playerTurnEl.style.fontSize = "20px";
        suspectOptionsEl.innerHTML = "<p style='color: #666; font-size: 16px; padding: 20px; background: #fff3cd; border-radius: 8px;'>You cannot vote. Your vote does not count towards your score.</p>";
        voteStatusEl.textContent = "Waiting for other players to vote...";
        voteStatusEl.style.color = "#666";
        quirkyLineEl.textContent = "🎭 As the Imposter, you cannot vote. Watch and wait!";
        voteTimerEl.style.display = "none"; // Hide timer for Imposter
        
        // Start polling to check when voting is complete
        startPolling();
      } else {
        // Regular player can vote
        renderVoteOptions();
        startTimer();
      }
    } catch (err) {
      console.error("Error initializing voting:", err);
      alert("Failed to load voting page. Refreshing page...");
      window.location.reload();
    }
  }

  // ----- Load clues for round -----
  async function loadCluesForRound(roundNumber) {
    try {
      const response = await window.API.Game.getCluesForRound(gameState.gameId, roundNumber);
      
      // API returns { clues: [...] }, extract the array
      const cluesArray = response.clues || response || [];
      
      // Ensure it's an array
      if (!Array.isArray(cluesArray)) {
        console.warn("Clues response is not an array:", cluesArray);
        return;
      }
      
      // Store clues by player_id
      cluesArray.forEach(clue => {
        if (clue && clue.player_id) {
          gameState.clues[clue.player_id] = clue.clue_word;
        }
      });
    } catch (err) {
      console.error("Error loading clues:", err);
      // Continue without clues if there's an error
    }
  }

  // ----- Render vote options -----
  function renderVoteOptions() {
    playerTurnEl.textContent = "Who do you think is the Imposter?";
    suspectOptionsEl.innerHTML = "";

    // Get other players (exclude self)
    const otherPlayers = gameState.players.filter(p => p.user_id !== currentUserId);

    if (otherPlayers.length === 0) {
      suspectOptionsEl.innerHTML = "<p>No other players to vote for.</p>";
      return;
    }

    otherPlayers.forEach(player => {
      const btn = document.createElement('button');
      const playerName = player.user_name || `Player ${player.seat_no}`;
      
      // Get clue for this player
      const clue = gameState.clues[player.id];
      const clueText = clue && clue !== "(skipped)" ? clue : "(no clue)";
      
      // Display player name and their clue
      btn.innerHTML = `<div style="font-weight: 600; margin-bottom: 4px;">${playerName}</div><div style="font-size: 14px; opacity: 0.8; font-style: italic;">Clue: ${clueText}</div>`;
      btn.style.textAlign = "left";
      btn.style.padding = "12px 16px";
      btn.onclick = () => submitVote(player.id, player.user_id);
      suspectOptionsEl.appendChild(btn);
    });
  }

  // ----- Submit vote -----
  async function submitVote(targetPlayerId, targetUserId) {
    if (!gameState.myPlayerId) {
      alert("Player ID not found. Please refresh the page.");
      return;
    }

    try {
      // Disable all buttons
      const buttons = suspectOptionsEl.querySelectorAll('button');
      buttons.forEach(btn => {
        btn.disabled = true;
        btn.style.opacity = "0.5";
      });

      voteStatusEl.textContent = "Submitting vote...";
      clearInterval(timer);

      const response = await window.API.Game.submitVote(
        gameState.gameId,
        gameState.myPlayerId,
        targetPlayerId
      );

      gameState.myVote = targetUserId;
      voteStatusEl.textContent = "Vote submitted! Waiting for others...";
      voteStatusEl.style.color = "#28a745";

      // Start polling to check when all votes are submitted
      startPolling();
    } catch (err) {
      console.error("Error submitting vote:", err);
      if (err.message && err.message.includes("Imposter cannot vote")) {
        // This shouldn't happen for regular players, but handle it gracefully
        alert("You cannot vote. Refreshing page...");
        window.location.reload();
      } else {
        alert(err.message || "Failed to submit vote. Please try again.");
        // Re-enable buttons
        const buttons = suspectOptionsEl.querySelectorAll('button');
        buttons.forEach(btn => {
          btn.disabled = false;
          btn.style.opacity = "1";
        });
        startTimer();
      }
    }
  }

  // ----- Timer functions -----
  function updateTimerColor() {
    voteTimerEl.classList.remove("timer-orange", "timer-red");
    if (timeLeft <= 5) {
      voteTimerEl.classList.add("timer-red");
    } else {
      voteTimerEl.classList.add("timer-orange");
    }
  }

  function tick() {
    voteTimerEl.textContent = timeLeft;
    updateTimerColor();
    timeLeft--;

    if (timeLeft < 0) {
      clearInterval(timer);
      timer = null;
      // Time's up - skip voting (abstain)
      voteStatusEl.textContent = "Time's up! You didn't vote (abstained).";
      voteStatusEl.style.color = "#d32f2f";
      
      // Disable all vote buttons
      const buttons = suspectOptionsEl.querySelectorAll('button');
      buttons.forEach(btn => {
        btn.disabled = true;
        btn.style.opacity = "0.5";
      });
      
      // Mark that we've abstained
      gameState.hasAbstained = true;
      
      // Immediately trigger game end (time expired)
      // Compute scores with only submitted votes
      handleVotingTimeout();
    }
  }

  function startTimer() {
    if (timer) clearInterval(timer);
    timeLeft = 30;
    voteTimerEl.textContent = timeLeft;
    updateTimerColor();
    timer = setInterval(tick, 1000);
  }

  // ----- Polling for voting status -----
  // ----- Check if players left the lobby -----
  async function checkPlayersLeft() {
    try {
      const lobbyState = await window.API.Lobby.getState(lobbyId);
      if (lobbyState && lobbyState.players) {
        const currentMemberCount = lobbyState.players.length;
        
        // If we haven't set original count yet, set it
        if (gameState.originalPlayerCount === 0) {
          gameState.originalPlayerCount = currentMemberCount;
        }
        
        // Check if players left
        if (currentMemberCount < gameState.originalPlayerCount) {
          // Player left - interrupt game
          interruptGame("A player has left the lobby. The game has been interrupted.");
          return;
        }
        
        // Also check if we have less than 3 players (minimum required)
        if (currentMemberCount < 3) {
          interruptGame("Not enough players remaining. The game has been interrupted.");
          return;
        }
      }
    } catch (err) {
      console.error("Error checking players:", err);
    }
  }

  function interruptGame(message) {
    // Stop all timers and polling
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    if (gameState.playerCheckInterval) {
      clearInterval(gameState.playerCheckInterval);
      gameState.playerCheckInterval = null;
    }
    
    // Show alert and refresh
    alert(message);
    setTimeout(() => {
      window.location.reload();
    }, 2000);
  }

  async function checkVotingStatus() {
    try {
      // Method 1: Try to get game status
      try {
        const gameData = await window.API.Lobby.getGame(gameState.lobbyId);
        if (gameData && gameData.status === "finished") {
          // All votes submitted, compute scores and go to results
          await computeScoresAndRedirect();
          return;
        }
      } catch (err) {
        // If 404, game might be finished - try method 2
        if (err.status === 404 || err.message?.includes("No game")) {
          // Method 2: Check if scores are computed (indicates game is finished)
          await checkScoresAndRedirect();
          return;
        }
        // Other errors - log but continue
        console.warn("Error getting game status:", err);
      }
      
      // Method 3: Check votes count as backup
      await checkVotesAndRedirect();
    } catch (err) {
      console.error("Error checking voting status:", err);
    }
  }

  // ----- Check if scores are computed (indicates game finished) -----
  async function checkScoresAndRedirect() {
    try {
      // If scores are computed, game is finished
      await window.API.Game.getScores(gameState.gameId);
      // Scores exist, game is finished
      await computeScoresAndRedirect();
    } catch (err) {
      // Scores not computed yet, game not finished
      // This is expected, so we don't log it as an error
    }
  }

  // ----- Check votes count and redirect if all voted or timeout -----
  async function checkVotesAndRedirect() {
    try {
      // Get all votes for this game
      const votes = await window.API.Game.getVotes(gameState.gameId);
      
      // Count unique voters
      const voters = new Set(votes.map(v => v.voter_id));
      
      // Get non-imposter players
      const nonImposterPlayers = gameState.players.filter(p => !p.is_imposter);
      
      // Check if voting time has expired (30 seconds)
      const votingTimeExpired = voteStartTime && (Date.now() - voteStartTime) >= 30000;
      
      // If voting time expired, trigger game end (only count submitted votes)
      if (votingTimeExpired && !gameState.allVotesSubmitted) {
        // Time expired - compute scores with only submitted votes
        // This will only count players who actually voted
        try {
          // First, update game status to finished
          const gameData = await window.API.Lobby.getGame(gameState.lobbyId);
          if (gameData && gameData.status !== "finished") {
            // Compute scores - this will only count submitted votes
            await window.API.Game.computeScores(gameState.gameId);
          }
          // Check if scores are computed
          try {
            await window.API.Game.getScores(gameState.gameId);
            // Scores exist, game is finished
            await computeScoresAndRedirect();
            return;
          } catch (err2) {
            // Scores not computed yet, try again next poll
          }
        } catch (err) {
          // If compute fails, try to get scores (might already be computed)
          try {
            await window.API.Game.getScores(gameState.gameId);
            await computeScoresAndRedirect();
            return;
          } catch (err2) {
            // Still not computed, wait a bit more
            console.warn("Waiting for scores to be computed...");
          }
        }
      }
      
      // Check if all non-imposter players have voted
      const allVoted = nonImposterPlayers.every(p => voters.has(p.id));
      
      if (allVoted) {
        // All non-imposter players voted, check if scores are computed
        try {
          await window.API.Game.getScores(gameState.gameId);
          // Scores exist, game is finished
          await computeScoresAndRedirect();
        } catch (err) {
          // Scores not computed yet, wait a bit more
        }
      }
    } catch (err) {
      // Ignore errors in vote checking
    }
  }

  // ----- Handle voting timeout -----
  async function handleVotingTimeout() {
    // Mark that we've handled timeout to prevent multiple calls
    if (gameState.timeoutHandled) {
      return;
    }
    gameState.timeoutHandled = true;
    
    try {
      voteStatusEl.textContent = "Time expired. Computing scores...";
      
      // Compute scores with only submitted votes
      try {
        await window.API.Game.computeScores(gameState.gameId);
        // Wait a moment for backend to update game status
        await new Promise(resolve => setTimeout(resolve, 500));
      } catch (err) {
        console.warn("Error computing scores (will still redirect):", err);
        // Continue even if compute fails
      }
      
      // Always redirect to results page after timeout
      voteStatusEl.textContent = "Redirecting to results...";
      setTimeout(() => {
        window.location.href = `/results?game_id=${gameState.gameId}&lobby_id=${gameState.lobbyId}&code=${lobbyCode}`;
      }, 1000);
    } catch (err) {
      console.error("Error handling voting timeout:", err);
      // Still redirect even on error
      setTimeout(() => {
        window.location.href = `/results?game_id=${gameState.gameId}&lobby_id=${gameState.lobbyId}&code=${lobbyCode}`;
      }, 1000);
    }
  }

  async function computeScoresAndRedirect() {
    try {
      // Compute scores
      await window.API.Game.computeScores(gameState.gameId);
      
      // Redirect to results page
      setTimeout(() => {
        window.location.href = `/results?game_id=${gameState.gameId}&lobby_id=${gameState.lobbyId}&code=${lobbyCode}`;
      }, 1000);
    } catch (err) {
      console.error("Error computing scores:", err);
      // Still redirect to results
      setTimeout(() => {
        window.location.href = `/results?game_id=${gameState.gameId}&lobby_id=${gameState.lobbyId}&code=${lobbyCode}`;
      }, 1000);
    }
  }

  function startPolling() {
    // Poll every 2 seconds to check if all votes are submitted
    setInterval(() => {
      checkVotingStatus();
    }, 2000);
  }

  function startPlayerCheck() {
    // Check every 3 seconds if players left
    gameState.playerCheckInterval = setInterval(() => {
      checkPlayersLeft();
    }, 3000);
  }

  // ----- Chat functions -----
  async function loadChat() {
    try {
      const messages = await window.API.Game.getChat(gameState.gameId);
      renderChat(messages);
    } catch (err) {
      console.error("Error loading chat:", err);
    }
  }

  function renderChat(messages) {
    if (!chatBoxEl) return;
    
    chatBoxEl.innerHTML = "";
    
    if (messages.length === 0) {
      chatBoxEl.innerHTML = "<p style='color: #999; font-style: italic; text-align: center;'>No messages yet. Start the discussion!</p>";
      return;
    }

    // Create player map for seat numbers
    const playerMap = {};
    gameState.players.forEach(p => {
      playerMap[p.id] = p;
    });

    messages.forEach(msg => {
      // In voting phase, all players are anonymous and called "Detective"
      const senderName = "Detective";
      
      const msgEl = document.createElement('div');
      msgEl.className = 'chat-message';
      
      const time = new Date(msg.sent_at);
      const timeStr = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      
      msgEl.innerHTML = `
        <span class="sender">${senderName}:</span>
        <span>${escapeHtml(msg.message)}</span>
        <span class="time">${timeStr}</span>
      `;
      chatBoxEl.appendChild(msgEl);
    });

    // Scroll to bottom
    chatBoxEl.scrollTop = chatBoxEl.scrollHeight;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  async function sendChatMessage() {
    if (!chatInputEl || !gameState.myPlayerId) return;
    
    const message = chatInputEl.value.trim();
    if (!message) {
      return;
    }

    try {
      if (chatSendBtnEl) chatSendBtnEl.disabled = true;
      await window.API.Game.sendChat(gameState.gameId, gameState.myPlayerId, message);
      chatInputEl.value = "";
      
      // Reload chat to show new message
      await loadChat();
    } catch (err) {
      console.error("Error sending chat:", err);
      if (err.message && err.message.includes("Chat closed")) {
        alert("Chat is closed in this phase.");
      } else {
        alert(err.message || "Failed to send message. Please try again.");
      }
    } finally {
      if (chatSendBtnEl) chatSendBtnEl.disabled = false;
    }
  }

  function startChatPolling() {
    if (!chatBoxEl) return;
    
    // Load chat initially
    loadChat();
    
    // Poll chat every 2 seconds
    setInterval(() => {
      loadChat();
    }, 2000);
  }

  // Initialize
  initVoting();
  
  // Start chat polling after initialization (with delay to ensure elements exist)
  setTimeout(() => {
    if (chatBoxEl && chatInputEl && chatSendBtnEl) {
      startChatPolling();
      
      // Event listeners
      chatSendBtnEl.addEventListener('click', sendChatMessage);
      chatInputEl.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          sendChatMessage();
        }
      });
    }
  }, 1500);
}

