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
  
  // ---------- Backend stubs (replace with real endpoints) ----------
  const API = {
    async submitClue({ round, text }) {
      console.log('Stub: submitClue', { round, text });
      await new Promise(r => setTimeout(r, 300));
      return { ok: true };
    },
    async getSubmissions(round) {
      console.log('Stub: getSubmissions', round);
      await new Promise(r => setTimeout(r, 300));
      // Example data: mark one as imposter
      return [
        { user: 'BlueJay', text: 'Orbit', role: 'crewmate' },
        { user: 'Scarlet', text: 'Cheese', role: 'imposter' },
        { user: 'Clover', text: 'Moon', role: 'crewmate' }
      ];
    },
    async vote({ target }) {
      console.log('Stub: vote', target);
      await new Promise(r => setTimeout(r, 300));
      return { ok: true };
    }
  };
  
  // ---------- UI helpers ----------
  function fmtTime(t) {
    const m = String(Math.floor(t / 60)).padStart(2, '0');
    const s = String(t % 60).padStart(2, '0');
    return `${m}:${s}`;
  }
  