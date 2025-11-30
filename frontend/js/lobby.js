// Wait for API to load
document.addEventListener('DOMContentLoaded', () => {
  // Load API script if not already loaded
  if (!window.API) {
    const script = document.createElement('script');
    script.src = '/js/api.js';
    document.head.appendChild(script);
    script.onload = initLobbyPage;
  } else {
    initLobbyPage();
  }
});

function initLobbyPage() {
  // Check authentication
  if (!requireAuth()) {
    return; // Redirect to login if not authenticated
  }
  
  // ----- Get lobby code and ID from URL -----
  const params = new URLSearchParams(window.location.search);
  const lobbyCode = params.get("code");
  const lobbyId = params.get("lobby_id");
  
  // Update lobby code display
  const lobbyCodeEl = document.getElementById("lobbyCode");
  const lobbyCodeBox = document.getElementById("lobbyCodeBox");
  if (lobbyCode) {
    if (lobbyCodeEl) {
      lobbyCodeEl.innerText = lobbyCode;
    }
    if (lobbyCodeBox) {
      lobbyCodeBox.innerText = lobbyCode;
      lobbyCodeBox.style.display = "block";
    }
  }

  // ----- Elements -----
  const playerListEl = document.getElementById("playerList");
  const waitingMsgEl = document.getElementById("statusMsg");
  const startGameBtn = document.getElementById("startGameBtn");

  // ----- Cache current user ID from token at page load -----
  // This prevents issues when localStorage is shared across windows
  let cachedUserId = null;
  function getCachedUserId() {
    if (cachedUserId) {
      return cachedUserId;
    }
    // Try to get from JWT token first (most reliable, per-window)
    const token = (window.API && window.API.getAuthToken) 
      ? window.API.getAuthToken() 
      : localStorage.getItem('imposter_auth_token');
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.sub) {
          cachedUserId = parseInt(payload.sub);
          return cachedUserId;
        }
      } catch (e) {
        console.warn('Failed to decode JWT token:', e);
      }
    }
    // Fallback to API method
    if (window.API && window.API.getCurrentUserId) {
      cachedUserId = window.API.getCurrentUserId();
    } else {
      cachedUserId = 1;
    }
    return cachedUserId;
  }

  let isHost = false;
  let currentLobbyId = lobbyId;
  let currentLobbyState = null;

  // ----- Poll real API every 2 seconds -----
  async function updateLobby() {
    try {
        if (!currentLobbyId && lobbyCode) {
            // Get lobby ID from code first
            const state = await window.API.Lobby.getStateByCode(lobbyCode);
            if (state && state.lobby) {
                currentLobbyId = state.lobby.id;
            }
        }

        if (!currentLobbyId) {
            console.error("No lobby ID available");
            return;
        }

        const data = await window.API.Lobby.getState(currentLobbyId);
        currentLobbyState = data;

        if (!playerListEl) return;

        playerListEl.innerHTML = "";

        // Get current user ID (use cached version to avoid localStorage conflicts)
        const currentUserId = getCachedUserId();
        
        // Debug: log current user ID for troubleshooting
        if (window.DEBUG) {
            console.log('Current user ID:', currentUserId, 'Host ID:', data.lobby?.host_id);
        }
        
        // Check if current user is host
        if (data.lobby) {
            isHost = data.lobby.host_id === currentUserId;
            
            // If game has started, redirect all players to game page
            if (data.lobby.status === "playing" && data.active_game_id) {
                window.location.href = `/game?lobby_id=${currentLobbyId}&game_id=${data.active_game_id}&code=${lobbyCode || ''}`;
                return; // Stop further processing
            }
        }

        // Render player list
        if (data.players && Array.isArray(data.players)) {
            if (data.players.length === 0) {
                playerListEl.innerHTML = "<li>No players yet. Waiting for players to join...</li>";
            } else {
                // Clear previous list
                playerListEl.innerHTML = "";
                
                // Render player list - user names are now included in API response
                data.players.forEach((player) => {
                    const li = document.createElement("li");
                    li.classList.add("player-card");
                    
                    // Use user_name from API response if available, otherwise use fallback
                    if (player.user_name) {
                        li.innerText = player.user_name;
                    } else {
                        li.innerText = `Player ${player.seat_no}`;
                    }
                    
                    // Mark current user
                    if (player.user_id === currentUserId) {
                        li.innerText += " (You)";
                    }
                    
                    playerListEl.appendChild(li);
                });
            }
        } else {
            playerListEl.innerHTML = "<li>No players found.</li>";
        }

        // Start button logic (HOST + at least 3 players)
        const playerCount = data.players ? data.players.length : 0;
        if (isHost && playerCount >= 3) {
            enableStartButton();
            waitingMsgEl.innerText = `Ready to start! (${playerCount} players)`;
        } else if (isHost && playerCount < 3) {
            disableStartButton();
            waitingMsgEl.innerText = `Waiting for players... (${playerCount}/3 minimum)`;
        } else {
            // Not host - hide button and show waiting message
            if (startGameBtn) {
                startGameBtn.style.display = "none";
            }
            if (playerCount >= 3) {
                waitingMsgEl.innerText = "Waiting for host to start the game...";
            } else {
                waitingMsgEl.innerText = `Waiting for players... (${playerCount}/3 minimum)`;
            }
        }

    } catch (err) {
        console.error("Error updating lobby:", err);
        if (playerListEl) {
            playerListEl.innerHTML = "<li>Error loading players.</li>";
        }
        if (waitingMsgEl) {
            waitingMsgEl.innerText = "Unable to fetch lobby state.";
        }
        disableStartButton();
    }
}

// ----- Enable Start button (GREEN) -----
function enableStartButton() {
    if (startGameBtn) {
        startGameBtn.disabled = false;
        startGameBtn.style.display = "block";
        startGameBtn.classList.add("active");
        startGameBtn.style.backgroundColor = "#28a745";   // GREEN like original
    }
}

// ----- Disable Start button (GREY) -----
function disableStartButton() {
    if (startGameBtn) {
        startGameBtn.disabled = true;
        startGameBtn.style.display = "block";
        startGameBtn.classList.remove("active");
        startGameBtn.style.backgroundColor = "#777";      // match original grey
    }
}

  // ----- Host clicks start game -----
  if (startGameBtn) {
    startGameBtn.addEventListener("click", async () => {
        if (!isHost || !currentLobbyId) return;
        
        try {
            const userId = getCachedUserId();
            const result = await window.API.Lobby.startGame(currentLobbyId, userId, 'aware');
            
            if (result && result.game_id) {
                // Redirect to game page
                window.location.href = `/game?lobby_id=${currentLobbyId}&game_id=${result.game_id}&code=${lobbyCode || ''}`;
            } else {
                alert("Failed to start game.");
            }
        } catch (err) {
            console.error("Error starting game:", err);
            alert(err.message || "Failed to start game.");
        }
    });
  }

  // ----- Start polling -----
  updateLobby();
  setInterval(updateLobby, 2000);
}
