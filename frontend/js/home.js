// Wait for API to load
document.addEventListener('DOMContentLoaded', () => {
  // Load API script if not already loaded
  if (!window.API) {
    const script = document.createElement('script');
    script.src = '/js/api.js';
    document.head.appendChild(script);
    script.onload = initHomePage;
  } else {
    initHomePage();
  }
});

function initHomePage() {
  // ----- Join Lobby -----
  async function joinLobby(codeInput) {
    try {
      const userId = window.API.getCurrentUserId();
      if (!userId) {
        alert("Please login first!");
        window.location.href = "/login";
        return;
      }

      const data = await window.API.Lobby.joinByCode(codeInput, userId);
      
      if (data.message) {
        // Success - redirect to lobby
        window.location.href = `/lobby?code=${codeInput}&lobby_id=${data.lobby_id || ''}`;
      } else {
        alert("Failed to join lobby. Please check the code.");
      }
    } catch (err) {
      console.error("Join lobby error:", err);
      alert(err.message || "Failed to join lobby. Please check the code.");
    }
  }

  // ----- Create Lobby -----
  async function createLobby() {
    try {
      const userId = window.API.getCurrentUserId();
      if (!userId) {
        alert("Please login first!");
        window.location.href = "/login";
        return;
      }

      const data = await window.API.Lobby.create(userId);
      
      if (data.code) {
        // Success - redirect to lobby
        window.location.href = `/lobby?code=${data.code}&lobby_id=${data.lobby_id}`;
      } else {
        alert("Failed to create lobby.");
      }
    } catch (err) {
      console.error("Create lobby error:", err);
      alert(err.message || "Failed to create lobby.");
    }
  }
  
  // ----- Event Listeners -----
  const joinBtn = document.getElementById("joinLobbyBtn");
  const createBtn = document.getElementById("createLobbyBtn");
  
  if (joinBtn) {
    joinBtn.addEventListener("click", () => {
      const codeInput = document.getElementById("joinCodeInput")?.value.trim() || 
                       document.getElementById("lobbyCode")?.value.trim();
      if (!codeInput || codeInput.length === 0) {
        alert("Please enter a lobby code.");
        return;
      }
      joinLobby(codeInput);
    });
  }
  
  if (createBtn) {
    createBtn.addEventListener("click", createLobby);
  }

  // Also handle the onclick handlers from HTML
  window.startLobby = createLobby;
  window.joinLobby = function() {
    const codeInput = document.getElementById("lobbyCode")?.value.trim();
    if (!codeInput) {
      alert("Please enter a lobby code!");
      return;
    }
    joinLobby(codeInput);
  };
}
  