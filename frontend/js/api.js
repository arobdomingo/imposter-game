/**
 * API Client for Imposter Game
 * Handles all API calls to the backend
 */

const API_BASE_URL = window.location.origin; // Use same origin as frontend

// Get current user ID from JWT token (preferred) or localStorage (fallback)
function getCurrentUserId() {
    // First try to get from JWT token (more reliable)
    const token = getAuthToken();
    if (token) {
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            if (payload.sub) {
                const userId = parseInt(payload.sub);
                // Also update localStorage to keep it in sync
                localStorage.setItem('current_user_id', userId.toString());
                return userId;
            }
        } catch (e) {
            // Token decode failed, fall back to localStorage
            console.warn('Failed to decode JWT token:', e);
        }
    }
    // Fallback to localStorage (for backwards compatibility)
    const storedId = localStorage.getItem('current_user_id');
    if (storedId) {
        return parseInt(storedId);
    }
    // Last resort: return 1 (should not happen if user is logged in)
    console.warn('No user ID found in token or localStorage');
    return 1;
}

// Get current user token (if using JWT)
function getAuthToken() {
    return localStorage.getItem('imposter_auth_token');
}

// Export getAuthToken to window.API for use in other scripts
if (typeof window !== 'undefined') {
    window.API = window.API || {};
    window.API.getAuthToken = getAuthToken;
}

// Helper function for API calls
async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    // Add auth token if available
    const token = getAuthToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(url, {
            ...options,
            headers
        });

        if (!response.ok) {
            // For 404 errors, try to get error message from response
            let errorDetail = response.statusText;
            try {
                const error = await response.json();
                errorDetail = error.detail || error.message || response.statusText;
            } catch {
                // If response is not JSON, use status text
                errorDetail = response.statusText;
            }
            
            // Create error with status code info
            const error = new Error(errorDetail);
            error.status = response.status;
            error.statusCode = response.status;  // Also set statusCode for compatibility
            throw error;
        }

        // Handle 204 No Content
        if (response.status === 204) {
            return null;
        }

        return await response.json();
    } catch (error) {
        // Only log non-404 errors (404 is expected for missing resources)
        // Check both status and statusCode properties
        if (error.status !== 404 && error.statusCode !== 404) {
            console.error(`API Error [${endpoint}]:`, error);
        }
        throw error;
    }
}

// User API
const UserAPI = {
    async create(name, email, password) {
        return apiCall('/v2/users/', {
            method: 'POST',
            body: JSON.stringify({ name, email, password })
        });
    },

    async login(email, password) {
        const response = await apiCall('/v2/authentications/', {
            method: 'POST',
            body: JSON.stringify({ 
                email: email,  // Use email for login
                password: password
                // expiry is optional, will default to 1 hour
            })
        });
        
        // Extract token and user ID
        const token = response.jwt || response.token;
        const userId = response.user_id || response.id;
        
        if (token) {
            localStorage.setItem('imposter_auth_token', token);
        }
        
        if (userId) {
            localStorage.setItem('current_user_id', userId.toString());
        } else if (token) {
            // Try to extract user ID from JWT token as fallback
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                if (payload.sub) {
                    localStorage.setItem('current_user_id', payload.sub.toString());
                }
            } catch (e) {
                console.warn('Could not extract user ID from token:', e);
            }
        }
        
        return {
            token: token,
            jwt: token,
            user_id: userId || localStorage.getItem('current_user_id')
        };
    },

    async getById(userId) {
        const response = await apiCall(`/v2/users/${userId}`);
        // API returns {"user": {...}}, so extract the user object
        return response.user || response;
    },

    async getByName(userName) {
        return apiCall(`/v2/users/${userName}`);
    }
};

// Lobby API
const LobbyAPI = {
    async create(hostId) {
        return apiCall('/v2/lobbies/', {
            method: 'POST',
            body: JSON.stringify({ host_id: hostId })
        });
    },

    async joinByCode(code, userId) {
        return apiCall(`/v2/lobbies/code/${code}/join`, {
            method: 'POST',
            body: JSON.stringify({ user_id: userId })
        });
    },

    async joinById(lobbyId, userId) {
        return apiCall(`/v2/lobbies/${lobbyId}/join`, {
            method: 'POST',
            body: JSON.stringify({ user_id: userId })
        });
    },

    async leave(lobbyId, userId) {
        return apiCall(`/v2/lobbies/${lobbyId}/leave`, {
            method: 'POST',
            body: JSON.stringify({ user_id: userId })
        });
    },

    async getState(lobbyId) {
        return apiCall(`/v2/lobbies/${lobbyId}`);
    },

    async getStateByCode(code) {
        return apiCall(`/v2/lobbies/code/${code}`);
    },

    async startGame(lobbyId, hostId, mode = 'aware') {
        return apiCall(`/v2/lobbies/${lobbyId}/start`, {
            method: 'POST',
            body: JSON.stringify({ host_id: hostId, mode })
        });
    },

    async getGame(lobbyId) {
        return apiCall(`/v2/lobbies/${lobbyId}/game`);
    },

    async getRole(gameId, userId) {
        return apiCall(`/v2/lobbies/${gameId}/role?user_id=${userId}`);
    },

    async endGame(lobbyId, hostId) {
        return apiCall(`/v2/lobbies/${lobbyId}/game/end`, {
            method: 'POST',
            body: JSON.stringify({ host_id: hostId })
        });
    }
};

// Game API
const GameAPI = {
    async getCluesForRound(gameId, roundNumber) {
        return apiCall(`/games/${gameId}/clues/${roundNumber}`);
    },

    async submitClue(gameId, playerId, roundNumber, clueWord, skipped = false) {
        return apiCall(`/games/${gameId}/clues/submit`, {
            method: 'POST',
            body: JSON.stringify({
                player_id: playerId,
                round_number: roundNumber,
                clue_word: clueWord,
                skipped
            })
        });
    },

    async submitVote(gameId, voterId, targetId) {
        return apiCall(`/games/${gameId}/votes`, {
            method: 'POST',
            body: JSON.stringify({
                voter_id: voterId,
                target_id: targetId
            })
        });
    },

    async getVotes(gameId) {
        return apiCall(`/games/${gameId}/votes`);
    },

    async getScores(gameId) {
        return apiCall(`/games/${gameId}/votes/score`);
    },

    async computeScores(gameId) {
        return apiCall(`/games/${gameId}/votes/score`, {
            method: 'POST'
        });
    },

    async getChat(gameId) {
        return apiCall(`/games/${gameId}/chat`);
    },

    async sendChat(gameId, playerId, message) {
        return apiCall(`/games/${gameId}/chat`, {
            method: 'POST',
            body: JSON.stringify({
                player_id: playerId,
                message
            })
        });
    }
};

// Leaderboard API
const LeaderboardAPI = {
    async getGlobalLeaderboard(limit = 100) {
        return apiCall(`/leaderboard/global?limit=${limit}`);
    },

    async getLobbyLeaderboard(lobbyId, limit = 100) {
        return apiCall(`/leaderboard/lobby/${lobbyId}?limit=${limit}`);
    }
};

// Export API
window.API = {
    User: UserAPI,
    Lobby: LobbyAPI,
    Game: GameAPI,
    Leaderboard: LeaderboardAPI,
    getCurrentUserId,
    getAuthToken
};

