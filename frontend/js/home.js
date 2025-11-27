// ----- Join Lobby -----
async function joinLobby(codeInput) {
    try {
      const res = await fetch("../mock/mock_lobby_join.json");
      const data = await res.json();
  
      if (!data.success) {
        alert(data.message || "Failed to join lobby.");
        return;
      }
  
      window.location.href = `lobby.html?code=${data.lobbyCode}`;
    } catch (err) {
      console.log("Join lobby error:", err);
      alert("Network or JSON error while joining.");
    }
  }
  
  // ----- Event Listeners -----
  document.getElementById("joinLobbyBtn").addEventListener("click", () => {
    const codeInput = document.getElementById("joinCodeInput").value.trim();
    if (codeInput.length === 0) {
      alert("Please enter a lobby code.");
      return;
    }
    joinLobby(codeInput);
  });
  
  document.getElementById("createLobbyBtn").addEventListener("click", () => {
    // Simulate creating a lobby with fixed code
    window.location.href = "lobby.html?code=AB12CD";
  });
  