// ----- Get lobby code from URL -----
const params = new URLSearchParams(window.location.search);
const lobbyCode = params.get("code");
document.getElementById("lobbyCode").innerText = lobbyCode;

// ----- Elements -----
const playerListEl = document.getElementById("playerList");
const waitingMsgEl = document.getElementById("statusMsg");
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
            disableStartButton();
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

        // Start button logic (HOST + 4 players)
        if (isHost && data.players.length === 4) {
            enableStartButton();
            waitingMsgEl.innerText = "Ready to start the game!";
        } else {
            disableStartButton();
            waitingMsgEl.innerText = "Waiting for players...";
        }

    } catch (err) {
        console.log("Error updating lobby:", err);
        playerListEl.innerHTML = "<li>Error loading players.</li>";
        waitingMsgEl.innerText = "Unable to fetch player list.";
        disableStartButton();
    }
}

// ----- Enable Start button (GREEN) -----
function enableStartButton() {
    startGameBtn.disabled = false;
    startGameBtn.classList.add("active");
    startGameBtn.style.backgroundColor = "#28a745";   // GREEN like original
}

// ----- Disable Start button (GREY) -----
function disableStartButton() {
    startGameBtn.disabled = true;
    startGameBtn.classList.remove("active");
    startGameBtn.style.backgroundColor = "#777";      // match original grey
}

// ----- Host clicks start game -----
startGameBtn.addEventListener("click", () => {
    if (!isHost) return;
    window.location.href = `game.html?code=${lobbyCode}`;
});

// ----- Start polling -----
updateLobby();
setInterval(updateLobby, 2000);
