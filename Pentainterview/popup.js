/**
 * popup.js
 * =========
 * Kết nối với background.js để nhận events và cập nhật UI.
 * KHÔNG tự kết nối WebSocket – mọi data đến qua chrome.runtime.sendMessage.
 */

// ── DOM refs ──────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const connPill        = $("connPill");
const connLabel       = $("connLabel");
const statusDot       = $("statusDot");
const statusText      = $("statusText");
const errorMsg        = $("errorMsg");
const transcriptBody  = $("transcriptBody");
const transcriptLen   = $("transcriptLen");
const suggestionBody  = $("suggestionBody");
const panelTranscript = $("panelTranscript");
const panelSuggestion = $("panelSuggestion");
const btnAsk          = $("btnAsk");
const btnAskLabel     = $("btnAskLabel");
const btnClear        = $("btnClear");
const btnReconnect    = $("btnReconnect");

// ── State ─────────────────────────────────────────────────────────────────────
let _loading    = false;
let _transcript    = "";
let _transcript_vi = "";
let _suggestion = "";
let _connected  = false;
let _status     = "idle";

// ── Render helpers ────────────────────────────────────────────────────────────

function renderConnection(connected) {
  _connected = connected;
  connPill.className   = `conn-pill ${connected ? "connected" : "disconnected"}`;
  connLabel.textContent = connected ? "Live" : "Offline";
  btnAsk.disabled       = !connected || _loading;
}

const STATUS_MAP = {
  idle:         { label: "Chờ câu hỏi...",           cls: "idle" },
  speaking:     { label: "🎙 Interviewer đang nói...", cls: "speaking" },
  transcribing: { label: "✦ Đang nhận dạng...",        cls: "transcribing" },
  disconnected: { label: "Mất kết nối – đang thử lại...", cls: "disconnected" },
};

function renderStatus(state) {
  _status = state;
  const s = STATUS_MAP[state] || STATUS_MAP.idle;
  statusDot.className   = `status-indicator ${s.cls}`;
  statusText.className  = `status-text ${s.cls}`;
  statusText.textContent = s.label;

  // Highlight transcript panel khi đang nói
  panelTranscript.classList.toggle("active", state === "speaking" || state === "transcribing");
}

function renderTranscript(full, full_vi) {
  _transcript    = full    ?? _transcript;
  _transcript_vi = full_vi ?? _transcript_vi;

  const wordCount = _transcript ? _transcript.split(/\s+/).filter(Boolean).length : 0;
  transcriptLen.textContent = wordCount ? `${wordCount} words` : "—";

  if (!_transcript) {
    transcriptBody.innerHTML = `<span class="empty-state">Chờ người phỏng vấn nói...</span>`;
    return;
  }

  const isBusy   = _status === "speaking" || _status === "transcribing";
  const cursor   = isBusy ? `<span class="cursor-blink"></span>` : "";

  if (_transcript_vi) {
    // Song ngữ: Việt (chính) + Anh (phụ)
    transcriptBody.innerHTML =
      `<div class="transcript-vi">
         <span class="lang-badge vi">VI</span>${escHtml(_transcript_vi)}${cursor}
       </div>
       <div class="transcript-en">
         <span class="lang-badge en">EN</span>${escHtml(_transcript)}
       </div>`;
  } else {
    // Chỉ tiếng Anh (dịch chưa xong hoặc bị lỗi)
    transcriptBody.innerHTML =
      `<div class="transcript-vi">
         <span class="lang-badge en">EN</span>${escHtml(_transcript)}${cursor}
       </div>`;
  }
}

function renderSuggestion(text, loading = false) {
  _suggestion = text;
  panelSuggestion.classList.toggle("active", !!text);

  if (loading) {
    suggestionBody.innerHTML =
      `<div class="skeleton" style="width:90%"></div>
       <div class="skeleton" style="width:75%"></div>
       <div class="skeleton"></div>`;
    return;
  }

  if (!text) {
    suggestionBody.innerHTML =
      `<span class="empty-state">Nhấn ⌘⇧A hoặc nút bên dưới để nhận gợi ý.</span>`;
    return;
  }

  // Render bullet points (• ...)
  const lines = text.split("\n").filter(l => l.trim());
  const html = lines.map(line => {
    const clean = line.replace(/^[•\-\*]\s*/, "").trim();
    if (!clean) return "";
    return `<div class="suggestion-line">
      <span class="bullet">•</span>
      <span>${escHtml(clean)}</span>
    </div>`;
  }).join("");

  suggestionBody.innerHTML = html || escHtml(text);
}

function renderLoading(loading) {
  _loading = loading;
  btnAsk.disabled = loading || !_connected;
  btnAskLabel.textContent = loading ? "Đang hỏi AI..." : "Lấy gợi ý";

  // Replace icon with spinner when loading
  const icon = btnAsk.querySelector("svg, .spin");
  if (loading) {
    if (icon && !icon.classList.contains("spin")) {
      const spinner = document.createElement("div");
      spinner.className = "spin";
      icon.replaceWith(spinner);
    }
  } else {
    const spinner = btnAsk.querySelector(".spin");
    if (spinner) {
      spinner.outerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:13px;height:13px">
        <line x1="22" y1="2" x2="11" y2="13"/>
        <polygon points="22 2 15 22 11 13 2 9 22 2"/>
      </svg>`;
    }
  }
}

function renderError(msg) {
  errorMsg.textContent = msg || "";
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Background Communication ──────────────────────────────────────────────────

/** Lắng nghe push events từ background.js */
chrome.runtime.onMessage.addListener((msg) => {
  console.log("[Popup] Received Message:", msg);
  renderError("");  // clear error on any event
  switch (msg.event) {
    case "connection":
      renderConnection(msg.data.connected);
      if (!msg.data.connected) renderStatus("disconnected");
      else if (_status === "disconnected") renderStatus("idle");
      break;

    case "status":
      renderStatus(msg.data.state);
      // Refresh transcript cursor blink
      if (_transcript) renderTranscript(_transcript);
      break;

    case "transcript":
      renderTranscript(msg.data.full, msg.data.full_vi);
      break;

    case "suggestion":
      renderSuggestion(msg.data.suggestion);
      break;

    case "loading":
      renderLoading(msg.data.loading);
      if (msg.data.loading) renderSuggestion("", true);
      break;

    case "error":
      renderError(msg.data.message);
      renderLoading(false);
      break;

    case "clear":
      renderTranscript("", "");
      renderSuggestion("");
      renderError("");
      renderStatus("idle");
      break;

    default:
      break;
  }
});

/** Bước đầu: load state hiện tại từ background */
async function initState() {
  try {
    const state = await chrome.runtime.sendMessage({ action: "get-state" });
    if (!state) return;

    renderConnection(!!state.isConnected);
    renderStatus(state.status || "idle");
    renderTranscript(state.transcript || "", state.transcript_vi || "");
    renderSuggestion(state.suggestion || "");
  } catch (e) {
    // Background chưa ready
    renderConnection(false);
    renderStatus("disconnected");
  }
}

// ── Button Handlers ───────────────────────────────────────────────────────────

btnAsk.addEventListener("click", () => {
  if (_loading || !_connected) return;
  renderError("");
  chrome.runtime.sendMessage({ action: "ask" }).catch(err => {
    renderError("Không thể kết nối với background script.");
  });
});

btnClear.addEventListener("click", () => {
  chrome.runtime.sendMessage({ action: "clear" });
});

btnReconnect.addEventListener("click", () => {
  chrome.runtime.sendMessage({ action: "reconnect" });
  renderStatus("idle");
  renderError("");
});

// ── Init ──────────────────────────────────────────────────────────────────────
initState();
