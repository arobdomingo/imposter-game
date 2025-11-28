// Wait for API to load
document.addEventListener('DOMContentLoaded', () => {
  // Load API script if not already loaded
  if (!window.API) {
    const script = document.createElement('script');
    script.src = '/js/api.js';
    document.head.appendChild(script);
    script.onload = initLeaderboardPage;
  } else {
    initLeaderboardPage();
  }
});

function initLeaderboardPage() {
  // Elements
  const leaderboardListEl = document.getElementById('leaderboardList');

  // ----- Initialize leaderboard page -----
  async function initLeaderboard() {
    try {
      await loadLeaderboard();
    } catch (err) {
      console.error("Error initializing leaderboard:", err);
      if (leaderboardListEl) {
        leaderboardListEl.innerHTML = "<li style='text-align: center; padding: 20px; color: #999;'>Error loading leaderboard. Please try again later.</li>";
      }
    }
  }

  // ----- Load leaderboard data -----
  async function loadLeaderboard() {
    try {
      const response = await window.API.Leaderboard.getGlobalLeaderboard();
      renderLeaderboard(response.entries);
    } catch (err) {
      console.error("Error loading leaderboard:", err);
      if (leaderboardListEl) {
        leaderboardListEl.innerHTML = "<li style='text-align: center; padding: 20px; color: #999;'>Error loading leaderboard. Please try again later.</li>";
      }
    }
  }

  // ----- Render leaderboard -----
  function renderLeaderboard(entries) {
    if (!leaderboardListEl) return;
    
    leaderboardListEl.innerHTML = "";

    if (entries.length === 0) {
      leaderboardListEl.innerHTML = "<li style='text-align: center; padding: 20px; color: #999;'>No scores yet. Play some games to see the leaderboard!</li>";
      return;
    }

    entries.forEach((entry, idx) => {
      const li = document.createElement('li');
      
      // Highlight top 3
      if (idx === 0) {
        li.classList.add('top');
      }
      
      // Rank emoji
      let rankDisplay = entry.rank;
      if (entry.rank === 1) {
        rankDisplay = '🥇';
      } else if (entry.rank === 2) {
        rankDisplay = '🥈';
      } else if (entry.rank === 3) {
        rankDisplay = '🥉';
      }
      
      li.innerHTML = `
        <span class="rank">${rankDisplay}</span>
        <span class="name">@${escapeHtml(entry.username)}</span>
        <span class="score">${entry.total_score} pts</span>
      `;
      
      leaderboardListEl.appendChild(li);
    });
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Initialize
  initLeaderboard();
}

