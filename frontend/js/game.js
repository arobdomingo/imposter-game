// Wait for API to load
document.addEventListener('DOMContentLoaded', () => {
  // Load API script if not already loaded
  if (!window.API) {
    const script = document.createElement('script');
    script.src = '/js/api.js';
    document.head.appendChild(script);
    script.onload = initGamePage;
  } else {
    initGamePage();
  }
});

function initGamePage() {
  // Get game info from URL
  const params = new URLSearchParams(window.location.search);
  const gameId = parseInt(params.get("game_id"));
  const lobbyId = parseInt(params.get("lobby_id"));
  const lobbyCode = params.get("code") || "";

  if (!gameId) {
    alert("Game ID not found. Redirecting to home...");
    window.location.href = "/home";
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
    currentRound: 1,
    myPlayer: null,
    myPlayerId: null,
    myWord: null,
    isImposter: false,
    players: [],
    submittedClues: {},
    gameStatus: "clue_submission",
    roleData: null,
    originalPlayerCount: 0,
    playerCheckInterval: null
  };

  // Elements
  const roleText = document.getElementById("roleText");
  const assignedWord = document.getElementById("assignedWord");
  const timerEl = document.getElementById("roundTimer");
  const previousCluesBox = document.getElementById("previousClues");
  const clueInput = document.getElementById("clueInput");
  const submitBtn = document.getElementById("submitClueBtn");
  const clueStatus = document.getElementById("clueStatus");

  // Timer - Imposter gets 50 seconds, others get 30 seconds
  let timeLeft = 30;
  let timer = null;
  let pollingInterval = null; // Store polling interval ID

  // ----- Initialize game -----
  async function initGame() {
    try {
      // Get player's role and word
      const roleData = await window.API.Lobby.getRole(gameId, currentUserId);
      gameState.roleData = roleData;
      gameState.myPlayerId = roleData.player_id;
      gameState.myWord = roleData.word;
      gameState.isImposter = roleData.is_imposter || false;
      
      // Set timer based on role: Imposter gets 50 seconds, others get 30
      timeLeft = gameState.isImposter ? 50 : 30;

      // Get game info to get players
      const gameData = await window.API.Lobby.getGame(lobbyId);
      if (gameData && gameData.players) {
        gameState.players = gameData.players;
        // Set original player count if not set
        if (gameState.originalPlayerCount === 0) {
          gameState.originalPlayerCount = gameData.players.length;
        }
        // Find my player object
        gameState.myPlayer = gameData.players.find(p => p.user_id === currentUserId);
        if (!gameState.myPlayer) {
          // Create a placeholder player object
          gameState.myPlayer = {
            user_id: currentUserId,
            seat_no: roleData.seat_no || 1
          };
        }
      }

      renderRoleAndWord();
      startPolling();
    } catch (err) {
      console.error("Error initializing game:", err);
      alert("Failed to load game. Redirecting...");
      window.location.href = "/home";
    }
  }

  // ----- Render role and word -----
  function renderRoleAndWord() {
    if (gameState.isImposter) {
      roleText.innerHTML = `&#127917; You are the IMPOSTER &mdash; Blend in&hellip; or be exposed`;
      assignedWord.innerText = gameState.myWord || "Blend. Trick. Survive.";
    } else {
      roleText.innerHTML = `&#128737; Your turn &mdash; Protect the secret word!`;
      assignedWord.innerText = gameState.myWord || "???";
    }
  }

  // ----- Check if it's my turn to submit -----
  async function checkMyTurn() {
    try {
      if (!gameState.myPlayerId) return false;

      // Try to submit a test clue to see if it's our turn
      // The API will return an error if it's not our turn
      // Actually, better approach: check if we've already submitted
      const mySubmitted = gameState.submittedClues[currentUserId]?.[gameState.currentRound];
      if (mySubmitted) {
        return false; // Already submitted
      }

      // Get all players and their clues for current round
      const players = gameState.players;
      if (!players || players.length === 0) return false;

      // Sort players by seat_no
      const sortedPlayers = [...players].sort((a, b) => (a.seat_no || 0) - (b.seat_no || 0));
      const mySeat = gameState.myPlayer?.seat_no || gameState.roleData?.seat_no || 1;

      // Check if all players before me have submitted
      // We'll check this by trying to submit (API will reject if not our turn)
      // Or we can poll for clues
      // For now, let's assume it's our turn if we haven't submitted
      // The API will handle the validation
      return true; // Let API handle turn validation
    } catch (err) {
      console.error("Error checking turn:", err);
      return false;
    }
  }

  // ----- Update previous clues display -----
  async function updatePreviousClues() {
    try {
      previousCluesBox.innerHTML = "";

      const players = gameState.players;
      if (!players || players.length === 0) return;

      // Imposter can see all submitted clues in real-time
      if (gameState.isImposter) {
        // Show all submitted clues for Imposter
        const sortedPlayers = [...players].sort((a, b) => (a.seat_no || 0) - (b.seat_no || 0));
        
        let hasClues = false;
        for (const player of sortedPlayers) {
          // Don't show own clue
          if (player.user_id === currentUserId) continue;
          
          const clue = gameState.submittedClues[player.user_id]?.[gameState.currentRound];
          if (clue) {
            hasClues = true;
            const row = document.createElement("div");
            row.style.margin = "4px 0";
            row.style.fontSize = "14px";
            const playerName = player.user_name || `Player ${player.seat_no}`;
            row.innerHTML = `<strong>${playerName}:</strong> ${clue}`;
            previousCluesBox.appendChild(row);
          }
        }
        
        if (!hasClues) {
          previousCluesBox.innerHTML = "<p style='color: #666;'>No clues submitted yet...</p>";
        }
      } else {
        // Regular players don't see clues until all are submitted
        previousCluesBox.innerHTML = "<p style='color: #666;'>Waiting for all players to submit...</p>";
      }
    } catch (err) {
      console.error("Error updating previous clues:", err);
    }
  }
  
  // ----- Update all clues (when all players submitted) -----
  async function updateAllClues() {
    try {
      previousCluesBox.innerHTML = "";

      const players = gameState.players;
      if (!players || players.length === 0) return;

      const sortedPlayers = [...players].sort((a, b) => (a.seat_no || 0) - (b.seat_no || 0));
      
      const header = document.createElement("p");
      header.style.fontWeight = "bold";
      header.style.marginBottom = "8px";
      header.innerText = "All Clues:";
      previousCluesBox.appendChild(header);
      
      for (const player of sortedPlayers) {
        const clue = gameState.submittedClues[player.user_id]?.[gameState.currentRound];
        if (clue) {
          const row = document.createElement("div");
          row.style.margin = "4px 0";
          row.style.fontSize = "14px";
          const playerName = player.user_name || `Player ${player.seat_no}`;
          const isMe = player.user_id === currentUserId;
          row.innerHTML = `<strong>${playerName}${isMe ? " (You)" : ""}:</strong> ${clue}`;
          previousCluesBox.appendChild(row);
        }
      }
    } catch (err) {
      console.error("Error updating all clues:", err);
    }
  }

  // ----- Timer functions -----
  function updateColor() {
    timerEl.classList.remove("timer-black", "timer-orange", "timer-red");
    if (timeLeft <= 5) {
      timerEl.classList.add("timer-red");
    } else if (timeLeft <= 10) {
      timerEl.classList.add("timer-orange");
    } else {
      timerEl.classList.add("timer-black");
    }
  }

  function tick() {
    timerEl.textContent = timeLeft;
    updateColor();
    timeLeft--;

    if (timeLeft < 0) {
      clearInterval(timer);
      onClueSubmitted("(skipped)");
    }
  }

  function startTimer() {
    if (timer) clearInterval(timer);
    // Don't reset timeLeft here - use the value set during initialization
    timerEl.textContent = timeLeft;
    updateColor();
    timer = setInterval(tick, 1000);
  }

  // ----- Submit clue -----
  async function onClueSubmitted(clueWord) {
    if (!gameState.myPlayerId) {
      alert("Player ID not found. Please refresh the page.");
      return;
    }

    try {
      clueInput.disabled = true;
      submitBtn.disabled = true;
      clueStatus.innerText = "Submitting clue...";
      clearInterval(timer);

      const skipped = clueWord === "(skipped)" || clueWord === "(no clue)";
      const clue = skipped ? "" : clueWord.trim();

      const response = await window.API.Game.submitClue(
        gameState.gameId,
        gameState.myPlayerId,
        gameState.currentRound,
        clue,
        skipped
      );

      // Store submitted clue
      if (!gameState.submittedClues[currentUserId]) {
        gameState.submittedClues[currentUserId] = {};
      }
      gameState.submittedClues[currentUserId][gameState.currentRound] = clue || "(skipped)";

      // Update previous clues from response
      // For Imposter: show all submitted clues immediately
      // For others: only store, will show after all submitted
      if (response.previous_clues) {
        response.previous_clues.forEach(pc => {
          // Find player by player_id or user_id
          const player = gameState.players.find(p => 
            p.id === pc.player_id || p.user_id === pc.user_id
          );
          if (player) {
            if (!gameState.submittedClues[player.user_id]) {
              gameState.submittedClues[player.user_id] = {};
            }
            gameState.submittedClues[player.user_id][gameState.currentRound] = pc.clue_word;
          } else if (pc.user_id) {
            // Store by user_id if player object not found
            if (!gameState.submittedClues[pc.user_id]) {
              gameState.submittedClues[pc.user_id] = {};
            }
            gameState.submittedClues[pc.user_id][gameState.currentRound] = pc.clue_word;
          }
        });
      }
      
      // Update display immediately for Imposter
      if (gameState.isImposter) {
        await updatePreviousClues();
      }

      clueStatus.innerText = "Clue submitted! Waiting for others...";

      // Check if all players submitted
      if (response.move_to_voting) {
        // All players submitted, show all clues to everyone, then move to voting
        // Stop polling and timer
        if (pollingInterval) {
          clearInterval(pollingInterval);
          pollingInterval = null;
        }
        if (timer) {
          clearInterval(timer);
          timer = null;
        }
        // Update clues display to show all clues
        await updateAllClues();
        clueStatus.innerText = "All clues submitted! Moving to voting...";
        setTimeout(() => {
          window.location.href = `/vote?game_id=${gameState.gameId}&lobby_id=${gameState.lobbyId}&code=${lobbyCode}`;
        }, 2000); // Give 2 seconds to see all clues
      } else {
        // Continue polling for other players' submissions
        // For Imposter, update clues display
        if (gameState.isImposter) {
          await updatePreviousClues();
        }
      }
    } catch (err) {
      console.error("Error submitting clue:", err);
      alert(err.message || "Failed to submit clue. Please try again.");
      clueInput.disabled = false;
      submitBtn.disabled = false;
      startTimer();
    }
  }

  // ----- Polling for game state -----
  async function pollGameState() {
    try {
      // Check game status first - if it's "voting", all players have submitted
      const gameData = await window.API.Lobby.getGame(gameState.lobbyId);
      if (gameData && gameData.status === "voting") {
        // All players submitted, show all clues and redirect to voting
        if (pollingInterval) {
          clearInterval(pollingInterval);
          pollingInterval = null;
        }
        if (timer) {
          clearInterval(timer);
          timer = null;
        }
        await updateAllClues();
        clueStatus.innerText = "All clues submitted! Moving to voting...";
        setTimeout(() => {
          window.location.href = `/vote?game_id=${gameState.gameId}&lobby_id=${gameState.lobbyId}&code=${lobbyCode}`;
        }, 2000);
        return; // Stop polling
      }

      // Check if we've already submitted
      const mySubmitted = gameState.submittedClues[currentUserId]?.[gameState.currentRound];
      
      if (!mySubmitted && clueInput.disabled && !clueStatus.innerText.includes("Submitting")) {
        // Haven't submitted yet, enable input
        clueInput.disabled = false;
        submitBtn.disabled = false;
        clueStatus.innerText = gameState.isImposter 
          ? "You're the Imposter! Enter a clue (you have 50 seconds and can see others' clues)."
          : "Enter your clue!";
        if (!timer) {
          startTimer();
        }
      } else if (mySubmitted) {
        // Already submitted, just update clues display
        clueStatus.innerText = "Clue submitted! Waiting for others...";
      }
      
      // For Imposter: poll for new clues from other players
      if (gameState.isImposter && !mySubmitted) {
        await fetchAndUpdateClues();
      }
      
      // Update clues display
      await updatePreviousClues();
    } catch (err) {
      console.error("Error polling game state:", err);
    }
  }

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
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
    if (gameState.playerCheckInterval) {
      clearInterval(gameState.playerCheckInterval);
      gameState.playerCheckInterval = null;
    }
    
    // Show alert and redirect
    alert(message);
    setTimeout(() => {
      window.location.href = `/lobby?lobby_id=${lobbyId}&code=${lobbyCode}`;
    }, 2000);
  }

  function startPlayerCheck() {
    // Check every 3 seconds if players left
    gameState.playerCheckInterval = setInterval(() => {
      checkPlayersLeft();
    }, 3000);
  }
  
  // ----- Fetch clues from API (for Imposter) -----
  async function fetchAndUpdateClues() {
    try {
      const response = await window.API.Game.getCluesForRound(gameState.gameId, gameState.currentRound);
      if (response && response.clues) {
        // Update submitted clues from API response
        response.clues.forEach(clueData => {
          if (clueData.user_id && clueData.user_id !== currentUserId) {
            if (!gameState.submittedClues[clueData.user_id]) {
              gameState.submittedClues[clueData.user_id] = {};
            }
            gameState.submittedClues[clueData.user_id][gameState.currentRound] = clueData.clue_word;
          }
        });
        // Update display
        await updatePreviousClues();
      }
    } catch (err) {
      // Silently handle errors (clues might not be available yet)
      if (err.status !== 404) {
        console.error("Error fetching clues:", err);
      }
    }
  }

  function startPolling() {
    // Clear any existing polling interval
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }
    
    // Initial setup
    if (!gameState.submittedClues[currentUserId]?.[gameState.currentRound]) {
      clueInput.disabled = false;
      submitBtn.disabled = false;
      clueStatus.innerText = gameState.isImposter 
        ? "You're the Imposter! Enter a clue (you have 50 seconds and can see others' clues)."
        : "Enter your clue!";
      startTimer();
    }
    
    // Initial poll
    pollGameState();
    
    // Poll every 2 seconds to update clues display (especially for Imposter)
    pollingInterval = setInterval(() => {
      pollGameState();
    }, 2000);

    // Start checking for players leaving
    startPlayerCheck();
  }

  // ----- Event listeners -----
  submitBtn.addEventListener("click", async () => {
    const clue = clueInput.value.trim();
    if (clue === "" && !clueInput.disabled) {
      clueStatus.innerText = "Please enter a clue!";
      return;
    }
    await onClueSubmitted(clue);
  });

  // Enter key to submit
  clueInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !clueInput.disabled) {
      submitBtn.click();
    }
  });

  // Initialize
  initGame();
}
