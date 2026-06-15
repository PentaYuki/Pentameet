/**
 * background.js – Service Worker
 * ================================
 */

const BACKEND_WS  = "ws://127.0.0.1:5005/socket.io/?EIO=4&transport=websocket";
const BACKEND_ASK = "http://127.0.0.1:5005/ask";
const BACKEND_HEALTH = "http://127.0.0.1:5005/health";
const RECONNECT_DELAY_MS = 3000;
const PING_ALARM = "ws-keepalive";

// ── State ─────────────────────────────────────────────────────────────────────
let socket       = null;
let isConnected  = false;
let transcript    = ""; 
let transcript_vi = ""; 
let lastStatus   = "disconnected";

// ── Storage helpers ───────────────────────────────────────────────────────────
async function saveState(patch) {
  console.log("[State] Saving:", patch);
  if (chrome.storage && chrome.storage.session) {
    return chrome.storage.session.set(patch);
  }
}

async function loadState() {
  if (chrome.storage && chrome.storage.session) {
    const state = await chrome.storage.session.get(["transcript", "suggestion", "status", "isConnected"]);
    console.log("[State] Loaded:", state);
    return state;
  }
  return {};
}

function broadcastToPopup(event, data) {
  chrome.runtime.sendMessage({ event, data }).catch(() => {
    // Popup closed
  });
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
function connect() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  console.log(`[WS] Connecting to ${BACKEND_WS}...`);
  
  fetch(BACKEND_HEALTH).then(res => {
    if (res.ok) console.log("[WS] Health check OK ✓");
  }).catch(err => {
    console.error("[WS] Health check failed:", err.message);
  });

  try {
    socket = new WebSocket(BACKEND_WS);
  } catch (e) {
    console.error("[WS] Error creating WebSocket:", e);
    scheduleReconnect();
    return;
  }

  socket.onopen = () => {
    console.log("[WS] ✓ Connected");
    isConnected = true;
    saveState({ isConnected: true, status: "idle" });
    broadcastToPopup("connection", { connected: true });
  };

  socket.onmessage = (event) => {
    handleSocketMessage(event.data);
  };

  socket.onerror = (err) => {
    console.error("[WS] WebSocket Error:", err);
  };

  socket.onclose = (event) => {
    console.log(`[WS] Disconnected. Code: ${event.code}, Reason: ${event.reason || "none"}. Reconnecting...`);
    isConnected = false;
    saveState({ isConnected: false, status: "disconnected" });
    broadcastToPopup("connection", { connected: false });
    scheduleReconnect();
  };
}

function scheduleReconnect() {
  setTimeout(connect, RECONNECT_DELAY_MS);
}

function handleSocketMessage(raw) {
  if (raw === "2") {
    socket.send("3");
    return;
  }

  if (raw.startsWith("0")) {
    console.log("[WS] Received OPEN. Sending CONNECT...");
    socket.send("40");
    return;
  }

  if (raw.startsWith("42")) {
    try {
      const payload = JSON.parse(raw.slice(2));
      const [eventName, eventData] = payload;
      console.log(`[WS] Received Event: ${eventName}`, eventData);
      handleBackendEvent(eventName, eventData);
    } catch (e) {
      console.warn("[WS] Parse error:", raw, e);
    }
  }
}

function handleBackendEvent(event, data) {
  switch (event) {
    case "transcript": {
      const text    = data?.text    || "";
      const text_vi = data?.text_vi || "";
      transcript    = transcript    ? `${transcript} ${text}`       : text;
      transcript_vi = transcript_vi ? `${transcript_vi} ${text_vi}` : text_vi;
      saveState({ transcript, transcript_vi });
      broadcastToPopup("transcript", { text, text_vi, full: transcript, full_vi: transcript_vi });
      break;
    }
    case "status": {
      const state = data?.state || "idle";
      lastStatus = state;
      saveState({ status: state });
      broadcastToPopup("status", { state });
      break;
    }
    default:
      break;
  }
}

async function askGemini() {
  const question = transcript.trim();
  if (!question) {
    broadcastToPopup("error", { message: "No transcript available." });
    return;
  }

  broadcastToPopup("loading", { loading: true });
  saveState({ suggestion: "" });

  try {
    const res = await fetch(BACKEND_ASK, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    const json = await res.json();
    if (json.error) throw new Error(json.error);

    const suggestion = json.suggestion || "";
    saveState({ suggestion });
    broadcastToPopup("suggestion", { suggestion });

    transcript = "";
    transcript_vi = "";
    saveState({ transcript: "", transcript_vi: "" });

  } catch (err) {
    console.error("[Ask] Error:", err);
    broadcastToPopup("error", { message: `Error: ${err.message}` });
  } finally {
    broadcastToPopup("loading", { loading: false });
  }
}

function clearAll() {
  transcript = "";
  transcript_vi = "";
  saveState({ transcript: "", transcript_vi: "", suggestion: "", status: lastStatus });
  broadcastToPopup("clear", {});
}

chrome.commands.onCommand.addListener((command) => {
  if (command === "get-suggestion") askGemini();
  if (command === "clear-all")      clearAll();
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === PING_ALARM) {
    if (isConnected && socket?.readyState === WebSocket.OPEN) {
      socket.send('42["ping",{}]');
    } else {
      connect();
    }
  }
});

// Start everything
chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(PING_ALARM, { periodInMinutes: 0.4 });
  connect();
});

chrome.runtime.onStartup.addListener(() => {
  connect();
});

// Initial call for when the SW wakes up
loadState().then(state => {
  if (state.transcript) transcript = state.transcript;
  if (state.transcript_vi) transcript_vi = state.transcript_vi;
  connect();
});

// ── Messages từ Popup ─────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  switch (msg.action) {
    case "get-state":
      loadState().then(sendResponse);
      return true; // async

    case "ask":
      askGemini().then(() => sendResponse({ ok: true }));
      return true;

    case "clear":
      clearAll();
      sendResponse({ ok: true });
      break;

    case "reconnect":
      connect();
      sendResponse({ ok: true });
      break;

    default:
      break;
  }
});
