// ----- Get lobby code from URL -----
const params = new URLSearchParams(window.location.search);
const lobbyCode = params.get("code");
document.getElementById("lobbyCode").innerText = "Lobby Code: " + lobbyCode;

// ----- Elements -----
const playerListEl = document.getElementById("playerList");
const waitingMsgEl = document.getElementById("waitingMsg");
const startGameBtn = document.getElementById("startGameBtn");

let isHost = false;

// ----- Poll mock API every 2 seconds -----
async function updateLobby() {
    try {
        const res = await fetch("../mock/mock_player_list.json");
        const data = await res.json();

        playerListEl.innerHTML = "";

        // Fallback if players array missing
        if (!data.players || !Array.isArray(data.players)) {
            console.log("Player list missing or invalid:", data.players);
            playerListEl.innerHTML = "<li>No players found.</li>";
            waitingMsgEl.innerText = "Waiting for players...";
            startGameBtn.disabled = true;
            startGameBtn.classList.remove("active");
            return;
        }

        // Render player list
        data.players.forEach(player => {
            const li = document.createElement("li");
            li.innerText = player;
            li.classList.add("player-card");
            playerListEl.appendChild(li);
        });

        // Host flag from JSON
        isHost = data.host;

        console.log("---- Lobby Update ----");
        console.log("Host:", isHost, "| Player count:", data.players.length);

        // ENABLE start button only when host + 4 players
        if (isHost && data.players.length === 4) {

            console.log("Condition met → enabling Start button…");
            console.log("Before enabling: disabled =", startGameBtn.disabled, "classes =", startGameBtn.classList.value);

            startGameBtn.disabled = false;        // IMPORTANT
            startGameBtn.classList.add("active");

            console.log("After enabling: disabled =", startGameBtn.disabled, "classes =", startGameBtn.classList.value);

            waitingMsgEl.innerText = "Ready to start the game!";

        } else {

            console.log("Condition NOT met → disabling Start button.");

            startGameBtn.disabled = true;
            startGameBtn.classList.remove("active");
            waitingMsgEl.innerText = "Waiting for players...";
        }

    } catch (err) {
        console.log("Error updating lobby:", err);
        playerListEl.innerHTML = "<li>Error loading players.</li>";
        waitingMsgEl.innerText = "Unable to fetch player list.";
    }
}

// ----- Host clicks start game -----
startGameBtn.addEventListener("click", () => {
    if (!isHost) return;
    window.location.href = `game.html?code=${lobbyCode}`;
});

// ----- Start polling -----
updateLobby();
setInterval(updateLobby, 2000);
