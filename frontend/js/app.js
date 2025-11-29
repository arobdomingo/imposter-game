/* Simple shared utilities and stubs for all pages */

// ---------- Auth context ----------
const Auth = {
    key: 'imposter_auth_token',
    get() { try { return localStorage.getItem(this.key); } catch { return null; } },
    set(token) { try { localStorage.setItem(this.key, token); } catch {} },
    clear() { try { localStorage.removeItem(this.key); } catch {} }
};

// ---------- Discord OAuth redirect ----------
function discordLogin() {
    const CLIENT_ID = 'DISCORD_CLIENT_ID';          // TODO: replace
    const REDIRECT_URI = 'DISCORD_REDIRECT_URI';    // TODO: replace
    const scope = 'identify';
    const params = new URLSearchParams({
        client_id: CLIENT_ID,
        redirect_uri: REDIRECT_URI,
        response_type: 'code',
        scope
    });
    window.location.href = `https://discord.com/oauth2/authorize?${params.toString()}`;
}

// ---------- Timer helper ----------
function createTimer(seconds, onTick, onDone) {
    let remaining = seconds;
    onTick?.(remaining);
    const id = setInterval(() => {
        remaining--;
        onTick?.(remaining);
        if (remaining <= 0) {
            clearInterval(id);
            onDone?.();
        }
    }, 1000);
    return () => clearInterval(id);
}

// ---------- Backend/API stubs ----------
const API = {
    token: Auth.get(),

    async submitClue({ round, text }) {
        console.log('Stub: submitClue', { round, text });
        await new Promise(r => setTimeout(r, 300));
        return { ok: true };
    },

    async getSubmissions(round) {
        console.log('Stub: getSubmissions', round);
        await new Promise(r => setTimeout(r, 300));
        return [
            { user: 'BlueJay', text: 'Orbit', role: 'crewmate' },
            { user: 'Scarlet', text: 'Cheese', role: 'imposter' },
            { user: 'Clover', text: 'Moon', role: 'crewmate' }
        ];
    },

    async vote({ voter, target }) {
        console.log('Stub: vote', { voter, target });
        await new Promise(r => setTimeout(r, 300));
        return { ok: true };
    },

    async getPlayers() {
        console.log('Stub: getPlayers');
        await new Promise(r => setTimeout(r, 300));
        // Example: current player names
        return ['Alice', 'Bob', 'Charlie', 'You'];
    }
};

// ---------- UI helpers ----------
function fmtTime(t) {
    const m = String(Math.floor(t / 60)).padStart(2, '0');
    const s = String(t % 60).padStart(2, '0');
    return `${m}:${s}`;
}

// ---------- Voting flow helpers ----------
class VoteManager {
    constructor(players, currentPlayer) {
        this.players = players.filter(p => p !== currentPlayer); // exclude self
        this.currentPlayerIndex = 0;
        this.currentPlayer = currentPlayer;
        this.votes = {};
    }

    getNextVoter() {
        if (this.currentPlayerIndex >= this.players.length) return null;
        return this.players[this.currentPlayerIndex++];
    }

    async submitVote(voter, target) {
        await API.vote({ voter, target });
        this.votes[voter] = target;
        return this.getNextVoter();
    }

    allVotesSubmitted() {
        return Object.keys(this.votes).length >= this.players.length;
    }
}

// Example usage on vote page
async function initVotingPage(currentPlayerName, onComplete) {
    const allPlayers = await API.getPlayers();
    const voteManager = new VoteManager(allPlayers, currentPlayerName);

    let voter = voteManager.getNextVoter();
    const voteContainer = document.getElementById('voteOptions');
    const voteBtn = document.getElementById('submitVoteBtn');

    function renderOptions() {
        voteContainer.innerHTML = '';
        voteManager.players.forEach(p => {
            if (p !== voter) {
                const btn = document.createElement('button');
                btn.textContent = p;
                btn.onclick = async () => {
                    voter = await voteManager.submitVote(voter, p);
                    if (!voter) {
                        onComplete(voteManager.votes);
                        window.location.href = '/results'; // go to results
                    } else {
                        renderOptions();
                    }
                };
                voteContainer.appendChild(btn);
            }
        });
    }

    renderOptions();
}
