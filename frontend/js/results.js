// Wait for API to load
document.addEventListener('DOMContentLoaded', () => {
  // Load API script if not already loaded
  if (!window.API) {
    const script = document.createElement('script');
    script.src = '/js/api.js';
    document.head.appendChild(script);
    script.onload = initResultsPage;
  } else {
    initResultsPage();
  }
});

function initResultsPage() {
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
    players: [],
    votes: [],
    scores: null,
    impostorIds: [],
    myPlayerId: null,
    isHost: false,
    lobbyCode: lobbyCode,
    lobbyMembers: [],
    originalPlayerCount: 0,
    lobbyPollInterval: null
  };

  // Elements
  const resultsListEl = document.getElementById('resultsList');
  const realImposterEl = document.getElementById('realImposter');
  const chatBoxEl = document.getElementById('chatBox');
  const chatInputEl = document.getElementById('chatInput');
  const chatSendBtnEl = document.getElementById('chatSendBtn');
  const startNextRoundBtn = document.getElementById('startNextRoundBtn');
  const playerLeftWarningEl = document.getElementById('playerLeftWarning');

  // ----- Initialize results page -----
  async function initResults() {
    try {
      // Get current player's role to get player_id
      try {
        const roleData = await window.API.Lobby.getRole(gameId, currentUserId);
        gameState.myPlayerId = roleData.player_id;
      } catch (err) {
        console.warn("Could not get role, chat may not work:", err);
      }

      // Get lobby state to check if current user is host and get members
      try {
        const lobbyState = await window.API.Lobby.getState(lobbyId);
        if (lobbyState && lobbyState.lobby) {
          gameState.isHost = lobbyState.lobby.host_id === currentUserId;
          
          // Get current lobby members
          if (lobbyState.players) {
            gameState.lobbyMembers = lobbyState.players;
          }
          
          // Show/hide start next round button for host
          if (startNextRoundBtn) {
            if (gameState.isHost) {
              startNextRoundBtn.style.display = "block";
            } else {
              startNextRoundBtn.style.display = "none";
            }
          }
        }
      } catch (err) {
        console.warn("Could not get lobby state:", err);
      }

      // Get game info to get players
      const gameData = await window.API.Lobby.getGame(lobbyId);
      if (gameData && gameData.players) {
        gameState.players = gameData.players;
        gameState.originalPlayerCount = gameData.players.length;
        
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
            if (err.status === 404 || err.statusCode === 404 || 
                (err.message && err.message.includes("User not found"))) {
              return {
                ...player,
                user_name: `Player ${player.seat_no || player.id}`
              };
            }
            // For other errors, return null name
            return {
              ...player,
              user_name: null
            };
          }
        });
        
        gameState.players = await Promise.all(playerPromises);
      }

      // Check if players left and update UI
      checkPlayersLeft();

      // Get votes
      const votes = await window.API.Game.getVotes(gameId);
      gameState.votes = votes;

      // Get scores (this also computes if not already computed)
      const scores = await window.API.Game.getScores(gameId);
      gameState.scores = scores;
      gameState.impostorIds = scores.impostor_ids || [];

      // Render results
      renderResults();

      // Check players left after all data is loaded
      checkPlayersLeft();

      // Start chat polling
      if (chatBoxEl && chatInputEl && chatSendBtnEl) {
        startChatPolling();
        setupChatListeners();
      }

      // Start polling lobby state to detect new game (for non-host players)
      if (!gameState.isHost) {
        startLobbyPolling();
      }
    } catch (err) {
      console.error("Error initializing results:", err);
      alert("Failed to load results. Refreshing page...");
      window.location.reload();
    }
  }

  // ----- Render results -----
  function renderResults() {
    resultsListEl.innerHTML = "";

    // Create player map for easy lookup
    const playerMap = {};
    gameState.players.forEach(p => {
      playerMap[p.id] = p;
    });

    // Get voter and target names
    const voteData = [];
    gameState.votes.forEach(vote => {
      const voter = playerMap[vote.voter_id];
      const target = playerMap[vote.target_id];
      if (voter && target) {
        voteData.push({
          voterName: voter.user_name || `Player ${voter.seat_no}`,
          targetName: target.user_name || `Player ${target.seat_no}`,
          voterId: vote.voter_id,
          targetId: vote.target_id
        });
      }
    });

    // Show each player's vote
    voteData.forEach(v => {
      const li = document.createElement('li');
      li.innerHTML = `<span class="name">@${v.voterName}</span> voted for <span class="votes">@${v.targetName}</span>`;
      resultsListEl.appendChild(li);
    });

    // Count votes per player
    const voteCount = {};
    gameState.players.forEach(p => {
      voteCount[p.id] = 0;
    });
    gameState.votes.forEach(v => {
      if (v.target_id) {
        voteCount[v.target_id] = (voteCount[v.target_id] || 0) + 1;
      }
    });

    // Show total votes
    const totalsHeader = document.createElement('li');
    totalsHeader.style.fontWeight = '700';
    totalsHeader.style.marginTop = '10px';
    totalsHeader.style.borderTop = '2px solid #ddd';
    totalsHeader.style.paddingTop = '10px';
    totalsHeader.textContent = 'Total Votes:';
    resultsListEl.appendChild(totalsHeader);

    gameState.players.forEach(p => {
      const count = voteCount[p.id] || 0;
      const playerName = p.user_name || `Player ${p.seat_no}`;
      const li = document.createElement('li');
      li.innerHTML = `<span class="name">@${playerName}</span><span class="votes">${count} vote${count !== 1 ? 's' : ''}</span>`;
      resultsListEl.appendChild(li);
    });

    // Show scores
    if (gameState.scores && gameState.scores.player_scores) {
      const scoresHeader = document.createElement('li');
      scoresHeader.style.fontWeight = '700';
      scoresHeader.style.marginTop = '10px';
      scoresHeader.style.borderTop = '2px solid #ddd';
      scoresHeader.style.paddingTop = '10px';
      scoresHeader.textContent = 'Scores:';
      resultsListEl.appendChild(scoresHeader);

      gameState.players.forEach(p => {
        const score = gameState.scores.player_scores[String(p.id)] || 0;
        const playerName = p.user_name || `Player ${p.seat_no}`;
        const li = document.createElement('li');
        li.innerHTML = `<span class="name">@${playerName}</span><span class="votes">${score} point${score !== 1 ? 's' : ''}</span>`;
        resultsListEl.appendChild(li);
      });
    }

    // Reveal real imposter(s)
    if (gameState.impostorIds.length > 0) {
      const impostorNames = gameState.impostorIds.map(impId => {
        const imp = playerMap[impId];
        if (imp) {
          return imp.user_name || `Player ${imp.seat_no}`;
        }
        return `Player ${impId}`;
      });
      
      if (impostorNames.length === 1) {
        realImposterEl.textContent = `@${impostorNames[0]}`;
      } else {
        realImposterEl.textContent = `@${impostorNames.join(', @')}`;
      }
    } else {
      realImposterEl.textContent = "@???";
    }
  }

  // ----- Chat functions -----
  async function loadChat() {
    try {
      const messages = await window.API.Game.getChat(gameState.gameId);
      renderChat(messages);
    } catch (err) {
      // Silently handle chat errors (game might be finished, chat might not be available)
      // Don't log 404, 429, or network errors (these are expected in some scenarios)
      const status = err.status || err.statusCode;
      if (status === 404 || status === 429) {
        // 404: Chat might not exist, 429: Rate limited (will retry)
        return;
      }
      // Only log unexpected errors
      if (err.message && 
          !err.message.includes("Failed to fetch") && 
          !err.message.includes("ERR_EMPTY_RESPONSE") &&
          !err.message.includes("Too Many Requests")) {
        console.error("Error loading chat:", err);
      }
    }
  }

  function renderChat(messages) {
    if (!chatBoxEl) return;
    
    chatBoxEl.innerHTML = "";
    
    if (messages.length === 0) {
      chatBoxEl.innerHTML = "<p style='color: #999; font-style: italic; text-align: center;'>No messages yet. Start the discussion!</p>";
      return;
    }

    // Create player map for names and impostor status
    const playerMap = {};
    gameState.players.forEach(p => {
      playerMap[p.id] = p;
    });

    messages.forEach(msg => {
      const player = playerMap[msg.player_id];
      const isImpostor = gameState.impostorIds.includes(msg.player_id);
      const playerName = player ? (player.user_name || `Player ${player.seat_no}`) : `Player ${msg.player_id}`;
      
      const msgEl = document.createElement('div');
      msgEl.className = 'chat-message';
      
      const time = new Date(msg.sent_at);
      const timeStr = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      
      const senderClass = isImpostor ? 'sender imposter' : 'sender';
      
      msgEl.innerHTML = `
        <span class="${senderClass}">${escapeHtml(playerName)}:</span>
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

  // ----- Poll lobby state to detect new game (for non-host players) -----
  async function checkLobbyForNewGame() {
    try {
      const lobbyState = await window.API.Lobby.getState(lobbyId);
      if (lobbyState && lobbyState.lobby) {
        // Check if a new game has started
        if (lobbyState.lobby.status === "playing" && lobbyState.active_game_id) {
          const newGameId = lobbyState.active_game_id;
          // Only redirect if it's a different game
          if (newGameId !== gameState.gameId) {
            // New game started - redirect
            window.location.href = `/game?lobby_id=${lobbyId}&game_id=${newGameId}&code=${gameState.lobbyCode || ''}`;
          }
        }
      }
    } catch (err) {
      // Silently handle errors
      console.warn("Error checking lobby for new game:", err);
    }
  }

  function startLobbyPolling() {
    // Poll every 2 seconds to check if host started a new game
    gameState.lobbyPollInterval = setInterval(() => {
      checkLobbyForNewGame();
    }, 2000);
  }

  function setupChatListeners() {
    if (!chatSendBtnEl || !chatInputEl) return;
    
    chatSendBtnEl.addEventListener('click', sendChatMessage);
    chatInputEl.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        sendChatMessage();
      }
    });
  }

  // ----- Check if players left the lobby -----
  function checkPlayersLeft() {
    if (!gameState.isHost) {
      // Not host - hide button
      if (startNextRoundBtn) {
        startNextRoundBtn.style.display = "none";
      }
      if (playerLeftWarningEl) {
        playerLeftWarningEl.style.display = "none";
      }
      return;
    }

    // Host - ensure button is visible
    if (startNextRoundBtn) {
      startNextRoundBtn.style.display = "block";
    }

    // Get current lobby member count
    const currentMemberCount = gameState.lobbyMembers ? gameState.lobbyMembers.length : 0;
    const originalPlayerCount = gameState.originalPlayerCount || 0;
    const playersLeft = originalPlayerCount > currentMemberCount;

    // Check if we have enough players (at least 3)
    const hasEnoughPlayers = currentMemberCount >= 3;

    if (playersLeft || !hasEnoughPlayers) {
      // Show warning and disable button
      if (playerLeftWarningEl) {
        playerLeftWarningEl.style.display = "block";
        if (!hasEnoughPlayers) {
          playerLeftWarningEl.innerHTML = `<p style="margin: 0; font-weight: 600;">⚠️ Not enough players. You need at least 3 players to start a new round. (Current: ${currentMemberCount})</p>`;
        } else {
          playerLeftWarningEl.innerHTML = `<p style="margin: 0; font-weight: 600;">⚠️ Some players have left the lobby. You need at least 3 players to start a new round. (Current: ${currentMemberCount})</p>`;
        }
      }
      if (startNextRoundBtn) {
        startNextRoundBtn.disabled = true;
        startNextRoundBtn.style.opacity = "0.6";
        startNextRoundBtn.style.cursor = "not-allowed";
      }
    } else {
      // Hide warning and enable button
      if (playerLeftWarningEl) {
        playerLeftWarningEl.style.display = "none";
      }
      if (startNextRoundBtn) {
        startNextRoundBtn.disabled = false;
        startNextRoundBtn.style.opacity = "1";
        startNextRoundBtn.style.cursor = "pointer";
      }
    }
  }

  // ----- Start next round (Host only) -----
  async function startNextRound() {
    if (!gameState.isHost || !gameState.lobbyId) {
      alert("Only the host can start the next round.");
      return;
    }

    // Re-check lobby members before starting
    try {
      const lobbyState = await window.API.Lobby.getState(lobbyId);
      if (lobbyState && lobbyState.players) {
        gameState.lobbyMembers = lobbyState.players;
        const currentMemberCount = lobbyState.players.length;
        const originalPlayerCount = gameState.originalPlayerCount || 0;
        const playersLeft = originalPlayerCount > currentMemberCount;
        
        // Check if players left
        if (playersLeft) {
          alert(`Cannot start a new round: Some players have left the lobby. You need at least 3 players. (Current: ${currentMemberCount}, Original: ${originalPlayerCount})`);
          checkPlayersLeft(); // Update UI
          return;
        }
        
        // Check if enough players
        if (currentMemberCount < 3) {
          alert(`Cannot start a new round. You need at least 3 players, but only ${currentMemberCount} player(s) are in the lobby.`);
          checkPlayersLeft(); // Update UI
          return;
        }
      }
    } catch (err) {
      console.error("Error checking lobby state:", err);
      alert("Failed to verify lobby members. Please try again.");
      return;
    }

    try {
      if (startNextRoundBtn) {
        startNextRoundBtn.disabled = true;
        startNextRoundBtn.textContent = "Starting...";
      }

      const userId = gameState.currentUserId;
      const result = await window.API.Lobby.startGame(gameState.lobbyId, userId, 'aware');
      
      if (result && result.game_id) {
        // Redirect to game page
        window.location.href = `/game?lobby_id=${gameState.lobbyId}&game_id=${result.game_id}&code=${gameState.lobbyCode || ''}`;
      } else {
        alert("Failed to start next round.");
        if (startNextRoundBtn) {
          startNextRoundBtn.disabled = false;
          startNextRoundBtn.textContent = "Start Next Round 🎮";
        }
      }
    } catch (err) {
      console.error("Error starting next round:", err);
      alert(err.message || "Failed to start next round. Please try again.");
      if (startNextRoundBtn) {
        startNextRoundBtn.disabled = false;
        startNextRoundBtn.textContent = "Start Next Round 🎮";
      }
      checkPlayersLeft(); // Update UI in case of error
    }
  }

  // Event listener for start next round button
  if (startNextRoundBtn) {
    startNextRoundBtn.addEventListener('click', startNextRound);
  }

  // Initialize
  initResults();
}

