/* Simple shared utilities and stubs for all pages */

// ---------- Auth context ----------
const Auth = {
    key: 'imposter_auth_token',
    get() { try { return localStorage.getItem(this.key); } catch { return null; } },
    set(token) { try { localStorage.setItem(this.key, token); } catch {} },
    clear() { try { localStorage.removeItem(this.key); } catch {} },
    
    // Check if user is authenticated
    isAuthenticated() {
        const token = this.get();
        if (!token) return false;
        
        // Check if token is expired
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const exp = payload.exp;
            if (exp && exp < Math.floor(Date.now() / 1000)) {
                // Token expired, clear it
                this.clear();
                return false;
            }
            return true;
        } catch (e) {
            // Invalid token format
            this.clear();
            return false;
        }
    }
};

// ---------- Require authentication ----------
// Call this function at the start of protected pages
function requireAuth(redirectTo = '/login') {
    // Skip check on login and register pages
    if (window.location.pathname === '/login' || window.location.pathname === '/register') {
        return true;
    }
    
    if (!Auth.isAuthenticated()) {
        // Store the intended destination for redirect after login
        const currentPath = window.location.pathname + window.location.search;
        if (currentPath !== redirectTo) {
            sessionStorage.setItem('redirectAfterLogin', currentPath);
        }
        window.location.href = redirectTo;
        return false;
    }
    return true;
}

// Auto-check authentication on page load for protected pages
(function autoCheckAuth() {
    // List of protected pages (pages that require authentication)
    const protectedPages = ['/home', '/lobby', '/game', '/vote', '/results', '/leaderboard'];
    const currentPath = window.location.pathname;
    
    // Check if current page is protected
    const isProtected = protectedPages.some(page => currentPath.startsWith(page));
    
    if (isProtected) {
        // Skip check on login and register pages
        if (currentPath !== '/login' && currentPath !== '/register') {
            if (!Auth.isAuthenticated()) {
                // Store the intended destination for redirect after login
                const fullPath = window.location.pathname + window.location.search;
                sessionStorage.setItem('redirectAfterLogin', fullPath);
                window.location.href = '/login';
                return;
            }
        }
    }
})();

// ---------- Discord OAuth redirect ----------
// Note: This function is now handled by the backend API endpoint
// Frontend should call /v2/authentications/discord/login which handles the OAuth flow
function discordLogin() {
    // Redirect to backend Discord login endpoint
    window.location.href = '/v2/authentications/discord/login';
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
