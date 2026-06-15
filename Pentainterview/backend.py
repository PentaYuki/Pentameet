"""
Interview Assistant Backend v2
===============================
Yêu cầu: pip install google-generativeai sounddevice faster-whisper flask flask-socketio torch googletrans==4.0.0-rc1

Cách chạy:
    export GEMINI_API_KEY="your_key_here"
    python backend.py

Lưu ý: Cần cài BlackHole 2ch driver trên macOS để capture audio từ Google Meet.
        Luôn dùng TAI NGHE khi phỏng vấn để tránh echo/loopback.
"""

import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Force select hub on macOS to avoid kqueue TypeError/IOClosed errors

import sys


import time
import queue
import threading
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from flask import Flask, request, jsonify, Response
from flask_socketio import SocketIO, emit
from ai_suggestion import get_suggestion, _build_system_prompt
import requests

# ─── Gemini Setup ──────────────────────────────────────────────────────────────
import google.genai as genai
from google.genai import types
from datetime import datetime, timedelta

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    print("[WARN] GEMINI_API_KEY not set - Using free Google Translate only")
    gemini_model = None
else:
    try:
        # New google.genai SDK uses direct client initialization
        gemini_model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            api_key=GEMINI_API_KEY
        )
        print("[Gemini] ✓ Initialized (API calls will be rate-limited)")
    except Exception as e:
        print(f"[Gemini] Error: {e} - Using free Google Translate only")
        gemini_model = None

# ─── Rate Limiter & Cache ──────────────────────────────────────────────────────
_gemini_cache = {}  # Cache translations to avoid duplicate API calls
_api_call_times = []  # Track API call times for rate limiting
MAX_API_CALLS_PER_HOUR = 10  # Conservative limit to avoid quota

def _is_rate_limited() -> bool:
    """Check if we've exceeded rate limit."""
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    # Remove old call times
    global _api_call_times
    _api_call_times = [t for t in _api_call_times if t > one_hour_ago]
    return len(_api_call_times) >= MAX_API_CALLS_PER_HOUR

def _record_api_call():
    """Record an API call for rate limiting."""
    global _api_call_times
    _api_call_times.append(datetime.now())

# ─── Cấu hình Audio & VAD ──────────────────────────────────────────────────────
SAMPLE_RATE     = 16000
BLOCK_SIZE      = 512          # ~32ms mỗi block
VAD_THRESHOLD   = 0.40         # Giảm xuống 0.4 để nhạy hơn
SILENCE_LIMIT   = 1.0          # giây im lặng để coi là hết câu (chỉnh 0.8–1.2)
MAX_BUFFER_SEC  = 30           # buffer tối đa 30 giây, tránh tốn RAM
KEEP_TAIL_SEC   = 0.5          # giữ lại 0.5s sau mỗi câu để không bị cắt âm đầu câu sau
BLACKHOLE_NAME  = "BlackHole 2ch"  # Tên thiết bị audio (macOS)

# ─── Flask & SocketIO ──────────────────────────────────────────────────────────
app = Flask(__name__)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet",
    logger=False,
    engineio_logger=False,
)

# ─── Faster-Whisper ────────────────────────────────────────────────────────────
print("[STT] Đang tải Whisper base...")
whisper_model = WhisperModel(
    "base",
    device="auto",           # dùng MPS nếu có, fallback CPU
    compute_type="float32",
)
print("[STT] Whisper ready ✓")

# ─── Silero VAD ────────────────────────────────────────────────────────────────
print("[VAD] Đang tải Silero VAD...")
import torch
vad_model, vad_utils = torch.hub.load(
    repo_or_dir="snakers4/silero-vad",
    model="silero_vad",
    force_reload=False,
    trust_repo=True,
)
(get_speech_timestamps, _, _, VADIterator, _) = vad_utils
print("[VAD] Silero VAD ready ✓")

# ─── Google Translate (miễn phí, không cần API key) ───────────────────────────
from googletrans import Translator

_translator = Translator()

def translate_to_vi(text: str, retries: int = 2) -> str:
    """
    Dịch text tiếng Anh → tiếng Việt.
    Chia nhỏ văn bản thành từng câu để tránh bị giới hạn ký tự/cụt bản dịch.
    """
    if not text.strip():
        return ""

    import re
    # Tách câu bằng dấu chấm, hỏi, cảm (nhưng giữ lại dấu)
    sentences = re.split(r'(?<=[.!?]) +', text)
    
    translated_parts = []
    global _translator
    
    for part in sentences:
        if not part.strip(): continue
        
        for attempt in range(retries + 1):
            try:
                result = _translator.translate(part, src="en", dest="vi")
                translated_parts.append(result.text.strip())
                break
            except Exception as e:
                if attempt == retries:
                    print(f"[Translate] Lỗi đoạn: '{part[:20]}...' -> {e}")
                    translated_parts.append(part) # Dùng tiếng Anh nếu lỗi
                time.sleep(0.3)
                
    vi_text = " ".join(translated_parts)
    print(f"[Translate] → {vi_text}")
    return vi_text




def translate_with_gemini(text: str, force: bool = False) -> str:
    """Dịch câu dài bằng Gemini (rate-limited, cacheable, fallback to Google Translate).
    
    Args:
        text: English text to translate
        force: If True, bypass rate limit (for manual requests)
    """
    if not text.strip():
        return ""
    
    # Check cache first
    cache_key = text[:100]  # Use first 100 chars as key
    if cache_key in _gemini_cache:
        print(f"[Gemini/Cache] Cache hit")
        return _gemini_cache[cache_key]
    
    # Check if Gemini is available and not rate limited
    if not gemini_model:
        print("[Gemini] Not configured, using Google Translate")
        return translate_to_vi(text)
    
    if _is_rate_limited() and not force:
        print(f"[Gemini] Rate limit reached ({len(_api_call_times)}/{MAX_API_CALLS_PER_HOUR}), using Google Translate")
        return translate_to_vi(text)

    prompt = (
        "Translate the following English interview segment into natural, concise Vietnamese.\n"
        "Rules:\n"
        "- If it's a long segment, summarize the core meaning so it's easy to read fast.\n"
        "- Use professional interview tone.\n"
        "- Return ONLY the translated/summarized text, NO introductory words, NO ellipses (...) at start/end.\n\n"
        f"English: {text}\n"
        "Vietnamese Concise Translation:"
    )

    try:
        response = gemini_model.generate_content(
            prompt,
            generation_config=types.GenerationConfig(
                max_output_tokens=500,
                temperature=0.2,
            ),
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE
                ),
            ]
        )
        if response.text:
            vi_text = response.text.strip().strip(".").strip("…")
            _gemini_cache[cache_key] = vi_text  # Cache result
            _record_api_call()  # Record for rate limiting
            print(f"[Gemini/Trans] ✓ Calls: {len(_api_call_times)}/{MAX_API_CALLS_PER_HOUR}")
            return vi_text
        else:
            print(f"[Gemini/Trans] Empty response, using Google Translate")
            return translate_to_vi(text)
    except Exception as e:
        print(f"[Gemini/Trans Error] {type(e).__name__}: {str(e)[:100]}")
        return translate_to_vi(text)


print("[Translate] Google Translate ready ✓ (miễn phí, không cần API key)")

# ─── State toàn cục ────────────────────────────────────────────────────────────
import queue
audio_queue = queue.Queue()

_state_lock = threading.Lock()
_audio_buffer   = np.array([], dtype=np.float32)
_is_speaking    = False
_last_speech_ts = 0.0
_speech_start   = 0          # index trong _audio_buffer lúc bắt đầu nói
_clients_count  = 0          # số extension đang kết nối

# ═══════════════════════════════════════════════════════════════════
# PHẦN 1 – State tích lũy transcript + event log cho iOS polling
# ═══════════════════════════════════════════════════════════════════

_full_transcript_en = ""   # Tích lũy toàn bộ phiên
_full_transcript_vi = ""
_last_status = "idle"

# Event log để iOS poll (giữ tối đa 100 event)
_event_log = []
_event_log_lock = threading.Lock()

MAX_EVENT_LOG = 100


def _log_event(event_type: str, data: dict):
    """Ghi event vào log để iOS poll."""
    entry = {"type": event_type, "data": data, "ts": time.time()}
    with _event_log_lock:
        _event_log.append(entry)
        if len(_event_log) > MAX_EVENT_LOG:
            del _event_log[:-MAX_EVENT_LOG]

# ─── Helpers ───────────────────────────────────────────────────────────────────

def _broadcast(event: str, data: dict):
    """Gửi event qua WebSocket VÀ ghi vào event log cho iOS."""
    global _full_transcript_en, _full_transcript_vi, _last_status

    # Tích lũy transcript
    if event == "transcript":
        txt    = data.get("text", "")
        txt_vi = data.get("text_vi", "")
        if txt:
            _full_transcript_en = (_full_transcript_en + " " + txt).strip()
        if txt_vi:
            _full_transcript_vi = (_full_transcript_vi + " " + txt_vi).strip()
        data["full_en"] = _full_transcript_en
        data["full_vi"] = _full_transcript_vi

    elif event == "status":
        _last_status = data.get("state", "idle")

    # Ghi vào event log
    _log_event(event, data)

    # Broadcast qua Socket.IO (Chrome Extension)
    try:
        data["_ts"] = time.time()
        # Chạy trong background thread native
        threading.Thread(target=socketio.emit, args=(event, data), kwargs={"namespace": "/"}, daemon=True).start()
    except Exception as e:
        print(f"[WS] Broadcast Error: {e}")


from typing import Optional, Union

def _find_blackhole_device() -> Optional[int]:
    """Tìm index thiết bị BlackHole trong danh sách sounddevice."""
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if BLACKHOLE_NAME.lower() in dev["name"].lower() and dev["max_input_channels"] > 0:
            return i
    return None


# ─── Audio Callback (chạy trong thread riêng của sounddevice) ─────────────────

def audio_callback(indata: np.ndarray, frames: int, time_info, status):
    """
    Được gọi mỗi BLOCK_SIZE mẫu (~32ms).
    Logic:
      1. Thêm chunk vào buffer.
      2. Chạy Silero VAD trên chunk.
      3. Nếu có giọng → đánh dấu is_speaking, gửi "speaking" event.
      4. Nếu im lặng > SILENCE_LIMIT → cắt câu, đưa vào queue STT.
    """
    global _audio_buffer, _is_speaking, _last_speech_ts, _speech_start

    if status:
        print(f"[AUDIO] Status: {status}")

    chunk = indata[:, 0].copy()  # mono float32
    peak = np.abs(chunk).max()
    if peak > 0.01: # Chỉ in khi có âm thanh đáng kể
        print(f"[DEBUG] Peak volume: {peak:.4f}", end="\r")

    with _state_lock:
        _audio_buffer = np.concatenate([_audio_buffer, chunk])

        # Giới hạn buffer để tránh tốn RAM
        max_samples = MAX_BUFFER_SEC * SAMPLE_RATE
        if len(_audio_buffer) > max_samples:
            overflow = len(_audio_buffer) - max_samples
            _audio_buffer    = _audio_buffer[overflow:]
            _speech_start = max(0, _speech_start - overflow)

        # Silero VAD: cần tensor float32
        chunk_tensor = torch.from_numpy(chunk)
        try:
            speech_prob = vad_model(chunk_tensor, SAMPLE_RATE).item()
        except Exception:
            speech_prob = 0.0

        now = time.monotonic()

        if speech_prob >= VAD_THRESHOLD:
            # ── Đang nói ──
            if not _is_speaking:
                # Bắt đầu câu mới
                _is_speaking  = True
                _speech_start = max(0, len(_audio_buffer) - len(chunk))
                # Cải tiến #1: báo Extension "đang nói"
                threading.Thread(target=_broadcast, args=("status", {"state": "speaking"}), daemon=True).start()
                print("[VAD] 🎙  Interviewer đang nói...", flush=True)
            _last_speech_ts = now

        else:
            # ── Im lặng ──
            if _is_speaking and (now - _last_speech_ts) > SILENCE_LIMIT:
                # Kết thúc câu
                _is_speaking = False

                # Lấy audio từ lúc bắt đầu nói đến cuối buffer
                # Trừ đi phần đuôi im lặng (~SILENCE_LIMIT giây)
                tail_samples = int(SILENCE_LIMIT * SAMPLE_RATE)
                end_idx = max(_speech_start + 1, len(_audio_buffer) - tail_samples)
                speech_audio = _audio_buffer[_speech_start:end_idx].copy()

                # Giữ đuôi nhỏ cho câu sau
                keep_samples = int(KEEP_TAIL_SEC * SAMPLE_RATE)
                _audio_buffer = _audio_buffer[-keep_samples:]
                _speech_start = 0

                if len(speech_audio) > SAMPLE_RATE * 0.3:  # Bỏ qua <0.3s
                    print(f"[VAD] ⏺ Đã kết thúc câu ({len(speech_audio)/SAMPLE_RATE:.2f}s). Đang gửi đi STT...", flush=True)
                    audio_queue.put(speech_audio)
                    threading.Thread(target=_broadcast, args=("status", {"state": "transcribing"}), daemon=True).start()
                else:
                    print("[VAD] ⏺ Bỏ qua câu quá ngắn.")
                    threading.Thread(target=_broadcast, args=("status", {"state": "idle"}), daemon=True).start()


# ─── Thread STT ────────────────────────────────────────────────────────────────

def stt_worker():
    """Lấy audio từ queue, chạy Whisper, gửi transcript qua WebSocket."""
    print("[STT] Worker đang chạy...", flush=True)
    while True:
        # print("[STT] Đang đợi audio từ queue...", flush=True)
        audio = audio_queue.get()
        print(f"[STT] Đã lấy audio từ queue ({len(audio)} mẫu).", flush=True)
        if audio is None:
            break

        try:
            print(f"[STT] Đang chạy Whisper transcribe...", flush=True)
            segments, info = whisper_model.transcribe(
                audio,
                beam_size=1,
                language="en",
                vad_filter=False,   # VAD đã xử lý ở ngoài rồi
                word_timestamps=False,
            )
            print("[STT] Transcription hoàn tất.")
            text = " ".join(seg.text.strip() for seg in segments).strip()

            if text:
                print(f"[Transcript EN] {text}")
                
                # Chỉ dùng Google Translate để tiết kiệm API Quota Gemini
                text_vi = translate_to_vi(text)

                _broadcast("transcript", {
                    "text":    text,      # Tiếng Anh gốc
                    "text_vi": text_vi,   # Tiếng Việt (rỗng nếu dịch lỗi)
                })
            else:
                _broadcast("status", {"state": "idle"})

        except Exception as e:
            print(f"[STT Error] {e}")
            _broadcast("status", {"state": "idle"})

        audio_queue.task_done()


# ─── Thread Audio Capture ──────────────────────────────────────────────────────

def audio_capture_worker():
    """Mở stream từ BlackHole và chạy liên tục."""
    device_idx = _find_blackhole_device()

    if device_idx is None:
        print(
            f"[ERROR] Không tìm thấy thiết bị '{BLACKHOLE_NAME}'.\n"
            "        Hãy cài BlackHole 2ch: https://github.com/ExistentialAudio/BlackHole"
        )
        return

    dev_info = sd.query_devices(device_idx)
    print(f"[Audio] Dùng thiết bị: {dev_info['name']} (index={device_idx})")
    print("[Audio] ⚠️  Hãy dùng TAI NGHE để tránh echo/loopback!")

    try:
        with sd.InputStream(
            device=device_idx,
            channels=1,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            callback=audio_callback,
            dtype="float32",
        ):
            print("[Audio] Stream đang chạy ✓")
            while True:
                time.sleep(0.5)
    except Exception as e:
        print(f"[Audio Error] {e}")


# ─── REST API: /ask ────────────────────────────────────────────────────────────
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    profile = data.get("profile", {})
    lang = data.get("lang", "en")

    if not question:
        return jsonify({"error": "Thiếu câu hỏi"}), 400

    print(f"[Ask] Q: {question[:60]}... (lang={lang})")
    result = get_suggestion(question, profile, lang=lang)

    if result["success"]:
        # IN RA ĐÂY
        print("\n" + "="*60)
        print("📌 GỢI Ý TRẢ LỜI ({}):".format(result["source"].upper()))
        print("="*60)
        print(result["suggestion"])
        print("="*60 + "\n")

        return jsonify({
            "suggestion": result["suggestion"],
            "source": result["source"]
        }), 200
    else:
        return jsonify({
            "error": result["suggestion"],
            "source": "error"
        }), 503
# ═══════════════════════════════════════════════════════════════════
# PHẦN 4 – 2 endpoint mới: /poll và /summarize
# ═══════════════════════════════════════════════════════════════════

@app.route("/poll", methods=["GET"])
def poll():
    """
    iOS polling endpoint.
    Query params:
      ?since=<unix_timestamp>  → chỉ trả events sau timestamp này
      ?full=1                  → trả full transcript hiện tại

    Response JSON:
    {
        "events": [...],      // events mới kể từ 'since'
        "transcript_en": "...",
        "transcript_vi": "...",
        "status": "idle|speaking|transcribing|...",
        "ts": <unix_timestamp>
    }
    """
    since = float(request.args.get("since", 0))

    with _event_log_lock:
        new_events = [e for e in _event_log if e["ts"] > since]

    return jsonify({
        "events":        new_events[-30:],
        "transcript_en": _full_transcript_en,
        "transcript_vi": _full_transcript_vi,
        "status":        _last_status,
        "ts":            time.time(),
    })


@app.route("/poll/clear", methods=["POST"])
def poll_clear():
    """iOS: xoá transcript tích lũy (đồng bộ với nút Clear)."""
    global _full_transcript_en, _full_transcript_vi
    _full_transcript_en = ""
    _full_transcript_vi = ""
    _log_event("clear", {})
    return jsonify({"ok": True})


@app.route("/summarize", methods=["POST"])
def summarize():
    """
    Đã vô hiệu hóa Gemini để tiết kiệm API Quota.
    Chỉ trả về thông báo để iOS hiển thị.
    """
    return jsonify({"summary_vi": "(Tính năng tóm tắt AI đã tắt để tiết kiệm Quota. Bạn vui lòng đọc bản dịch đầy đủ ở trên.)"})


@app.route("/ask/stream", methods=["POST"])
def ask_stream():
    """
    Streaming AI suggestion qua SSE (Server-Sent Events).
    Hỗ trợ Ollama local (stream: true).
    
    Body JSON: {"question": "...", "profile": {...}, "lang": "en"}
    Response: SSE stream (text/event-stream)
    
    Mỗi message SSE có format: data: {"token": "...", "source": "...", "error": "..."}
    Kết thúc bằng: data: [DONE]
    """
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    profile = data.get("profile", {})
    lang = data.get("lang", "en")

    if not question:
        return jsonify({"error": "Thiếu câu hỏi"}), 400

    print(f"[Ask/Stream] Q: {question[:60]}... (lang={lang})")

    # Đọc config Ollama từ ai_suggestion module
    from ai_suggestion import OLLAMA_BASE_URL, OLLAMA_MODEL

    def generate():
        """Generator function để stream tokens từ Ollama."""
        try:
            # Build prompt giống như trong ai_suggestion.py
            system_prompt = _build_system_prompt(profile)
            full_prompt = f"{system_prompt}\nInterviewer's question: {question}\nSuggested answer (English, bullet points):"

            # Gọi Ollama với stream=True
            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": full_prompt,
                    "stream": True,  # BẬT STREAM
                    "options": {
                        "temperature": 0.35,
                        "num_predict": 150,
                    }
                },
                timeout=30,
                stream=True,  # để requests cũng stream
            )

            if resp.status_code != 200:
                yield f"data: {json.dumps({'error': f'Ollama error {resp.status_code}'})}\n\n"
                print(f"[Ask/Stream] ✗ Ollama HTTP {resp.status_code}")
                return

            # Gửi source trước
            yield f"data: {json.dumps({'source': 'ollama'})}\n\n"

            # Đọc từng dòng JSON token từ Ollama
            full_response = ""
            for line in resp.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode())
                        token = chunk.get("response", "")
                        if token:
                            full_response += token
                            # Gửi token qua SSE
                            yield f"data: {json.dumps({'token': token})}\n\n"
                        # Khi done, Ollama gửi "done": true
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

            # IN RA RESPONSE CUỐI CÙNG
            if full_response:
                print("\n" + "="*60)
                print("📌 GỢI Ý TRẢ LỜI (OLLAMA - STREAM):")
                print("="*60)
                print(full_response)
                print("="*60 + "\n")

            # Kết thúc stream
            yield "data: [DONE]\n\n"

        except requests.exceptions.ConnectionError:
            yield f"data: {json.dumps({'error': 'Ollama not running. Start with: ollama serve'})}\n\n"
            print(f"[Ask/Stream] ✗ Ollama connection error")
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            print(f"[Ask/Stream] ✗ Error: {str(e)}")

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "whisper": "base",
        "llm": "gemini-flash-latest",
        "vad": "silero",
    })


# ─── Socket.IO Events ──────────────────────────────────────────────────────────

@socketio.on("connect")
def on_connect():
    global _clients_count
    _clients_count += 1
    print(f"[WS] Extension connected (total: {_clients_count})")
    emit("status", {"state": "idle"})


@socketio.on("disconnect")
def on_disconnect():
    global _clients_count
    _clients_count = max(0, _clients_count - 1)
    print(f"[WS] Extension disconnected (total: {_clients_count})")


@socketio.on("ping")
def on_ping(data):
    emit("pong", {"ts": time.time()})


# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Interview Assistant Backend v2")
    print("=" * 60)

    # Sử dụng luồng thật (native thread) cho các tác vụ nặng (STT, Audio Capture)
    threading.Thread(target=stt_worker, daemon=True).start()
    threading.Thread(target=audio_capture_worker, daemon=True).start()

    # Flask + SocketIO
    print("[Server] Khởi động tại http://0.0.0.0:5005")
    socketio.run(
        app,
        host="0.0.0.0",
        port=5005,
        debug=False,
        use_reloader=False,
    )
