const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
tg.setHeaderColor("#0a0e14");
tg.setBackgroundColor("#0a0e14");

const API_BASE =
  document.querySelector('meta[name="strike-api"]')?.content?.trim() ||
  window.location.origin;

const DISCLAIMER =
  "Entertainment only. STRIKECOINS have no cash value. Stars buy cosmetics only. Not gambling.";

async function api(path, body = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ init_data: tg.initData, ...body }),
  });
  const data = await res.json();
  if (data.error) throw new Error(data.error);
  return data;
}

function showError(msg) {
  let el = document.getElementById("error");
  if (!el) {
    el = document.createElement("div");
    el.id = "error";
    document.getElementById("app").prepend(el);
  }
  el.textContent = msg;
  el.hidden = !msg;
}

function renderCards(container, cards) {
  container.innerHTML = "";
  cards.forEach((c) => {
    const div = document.createElement("div");
    div.className = "card-chip" + (c === "?" ? " hidden-card" : "");
    div.textContent = c === "?" ? "?" : c;
    container.appendChild(div);
  });
}

function cardDisplay(v) {
  if (v === 11) return "A";
  if (v === 10) return "10";
  return String(v);
}

let profile = null;

async function loadProfile() {
  profile = await api("/api/v1/me");
  document.getElementById("balance").textContent =
    `${profile.strikecoins.toLocaleString()} SC`;
  addStrikeBubble(profile.strike_line);
  renderLeaderboard(profile.leaderboard, profile.room_code);
  if (profile.room_code) {
    document.getElementById("room-code").value = profile.room_code;
  }
}

function addStrikeBubble(text, user = false) {
  const chat = document.getElementById("strike-chat");
  const b = document.createElement("div");
  b.className = "bubble" + (user ? " user" : "");
  b.textContent = text;
  chat.appendChild(b);
  chat.scrollTop = chat.scrollHeight;
}

function renderLeaderboard(rows, code) {
  const ul = document.getElementById("leaderboard");
  ul.innerHTML = "";
  if (!rows?.length) {
    ul.innerHTML = "<li>No squad yet — create a room!</li>";
    return;
  }
  rows.forEach((r, i) => {
    const li = document.createElement("li");
    li.textContent = `${i + 1}. ${r.name} — ${r.strikecoins.toLocaleString()} SC`;
    ul.appendChild(li);
  });
  if (code) {
    document.getElementById("invite-link").textContent =
      `Room ${code} · invite friends via bot /invite`;
  }
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`panel-${btn.dataset.tab}`).classList.add("active");
  });
});

function showGame(g, message) {
  renderCards(document.getElementById("player-cards"), g.player_hand.map(cardDisplay));
  renderCards(document.getElementById("dealer-cards"), g.dealer_hand.map((c) => (c === "?" ? "?" : cardDisplay(c))));
  document.getElementById("player-val").textContent = g.player_value != null ? `(${g.player_value})` : "";
  document.getElementById("dealer-val").textContent = g.dealer_value != null ? `(${g.dealer_value})` : "";
  if (message) document.getElementById("game-status").textContent = message;
}

document.getElementById("btn-deal").addEventListener("click", async () => {
  try {
    showError("");
    const bet = parseInt(document.getElementById("bet").value, 10) || 100;
    const res = await api("/api/v1/play/start", { bet });
    profile.strikecoins = res.strikecoins;
    document.getElementById("balance").textContent = `${profile.strikecoins.toLocaleString()} SC`;
    showGame(res.game, "Hit or Stand?");
    document.getElementById("actions").hidden = false;
    document.getElementById("btn-deal").disabled = true;
    if (res.strike_line) addStrikeBubble(res.strike_line);
  } catch (e) { showError(e.message); }
});

async function doAction(action) {
  const res = await api("/api/v1/play/action", { action });
  profile.strikecoins = res.strikecoins;
  document.getElementById("balance").textContent = `${profile.strikecoins.toLocaleString()} SC`;
  showGame(res.game, res.message || "");
  if (res.strike_line) addStrikeBubble(res.strike_line);
  if (res.done) {
    document.getElementById("actions").hidden = true;
    document.getElementById("btn-deal").disabled = false;
    await loadProfile();
  }
}

document.getElementById("btn-hit").addEventListener("click", () => doAction("hit").catch((e) => showError(e.message)));
document.getElementById("btn-stand").addEventListener("click", () => doAction("stand").catch((e) => showError(e.message)));

document.getElementById("btn-strike-send").addEventListener("click", async () => {
  const input = document.getElementById("strike-msg");
  const msg = input.value.trim();
  if (!msg) return;
  addStrikeBubble(msg, true);
  input.value = "";
  try {
    const res = await api("/api/v1/strike/talk", { message: msg });
    addStrikeBubble(res.line);
  } catch (e) { showError(e.message); }
});

document.getElementById("btn-room-create").addEventListener("click", async () => {
  try {
    const res = await api("/api/v1/room/create");
    document.getElementById("room-code").value = res.code;
    document.getElementById("invite-link").textContent = res.invite;
    renderLeaderboard(res.leaderboard, res.code);
    await loadProfile();
  } catch (e) { showError(e.message); }
});

document.getElementById("btn-room-join").addEventListener("click", async () => {
  try {
    const code = document.getElementById("room-code").value.trim();
    const res = await api("/api/v1/room/join", { code });
    await loadProfile();
    addStrikeBubble(`Joined squad ${res.code}! Let's farm W's gng`);
  } catch (e) { showError(e.message); }
});

async function loadMusic() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/music`);
    const data = await res.json();
    const tracks = document.getElementById("tracks");
    tracks.innerHTML = "";
    data.tracks.forEach((t) => {
      const a = document.createElement("a");
      a.className = "btn track-btn";
      a.href = t.url;
      a.target = "_blank";
      a.textContent = `🎵 ${t.title}`;
      tracks.appendChild(a);
    });
    const live = document.getElementById("live-streams");
    data.live.forEach((s) => {
      const a = document.createElement("a");
      a.className = "btn live-btn";
      a.href = s.url;
      a.target = "_blank";
      a.textContent = `📻 ${s.name}`;
      live.appendChild(a);
    });
  } catch (_) {
    document.getElementById("tracks").textContent = "Use /music in the bot chat.";
  }
}

document.getElementById("disclaimer-link").addEventListener("click", (e) => {
  e.preventDefault();
  tg.showAlert(DISCLAIMER);
});

loadProfile().catch((e) => {
  showError(e.message + " — use /play in bot until API is deployed on Render.");
});
loadMusic();