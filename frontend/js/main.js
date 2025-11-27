// ------------------------------------
// CONFIG: switch this to false when backend is ready
// ------------------------------------
const USE_MOCK = true;

// Mock paths (frontend/mock/)
const MOCK_CREATE = "../mock/mock_lobby_create.json";
const MOCK_JOIN = "../mock/mock_lobby_join.json";

// Backend base URL (change if needed)
const BASE_URL = "http://127.0.0.1:8000";


// ------------------------------------
// CREATE LOBBY
// ------------------------------------
document.getElementById("createLobbyBtn").addEventListener("click", async () => {
    try {
        let data;

        if (USE_MOCK) {
            const res = await fetch(MOCK_CREATE);
            data = await res.json();
        } else {
            const res = await fetch(`${BASE_URL}/api/lobby/create`, {
                method: "POST"
            });
            data = await res.json();
        }

        if (!data.lobby_code) {
            alert("Error creating lobby. Try again.");
            return;
        }

        // Go to lobby page
        window.location.href = `pages/lobby.html?code=${data.lobby_code}`;

    } catch (error) {
        console.error("Create lobby error:", error);
        alert("Failed to create lobby. Backend may be offline.");
    }
});


// ------------------------------------
// JOIN LOBBY
// ------------------------------------
document.getElementById("joinLobbyBtn").addEventListener("click", async () => {
    const code = document.getElementById("lobbyCodeInput").value.trim();

    if (code === "") {
        alert("Please enter a lobby code.");
        return;
    }

    try {
        let data;

        if (USE_MOCK) {
            const res = await fetch(MOCK_JOIN);
            data = await res.json();
        } else {
            const res = await fetch(`${BASE_URL}/api/lobby/join`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ lobby_code: code })
            });
            data = await res.json();
        }

        if (data.success) {
            window.location.href = `pages/lobby.html?code=${code}`;
        } else {
            alert(data.message || "Invalid lobby code!");
        }

    } catch (error) {
        console.error("Join lobby error:", error);
        alert("Failed to join lobby. Backend may be offline.");
    }
});
