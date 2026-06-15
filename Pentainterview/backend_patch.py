"""
backend_patch.py
================
Các đoạn code CẦN THÊM VÀO backend.py để hỗ trợ iOS companion app.

HƯỚNG DẪN:
1. Thêm PHẦN 1 vào ngay sau dòng `_clients_count  = 0`
2. Thay toàn bộ hàm `_broadcast` bằng PHẦN 2
3. Thay toàn bộ endpoint `/ask` bằng PHẦN 3
4. Thêm PHẦN 4 (2 endpoint mới) trước endpoint `/health`
"""

import json

# ═══════════════════════════════════════════════════════════════════
# PHẦN 1 – State tích lũy transcript + event log cho iOS polling
# Thêm vào ngay sau: _clients_count  = 0
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


# ═══════════════════════════════════════════════════════════════════
# PHẦN 2 – Thay thế hàm _broadcast
# ═══════════════════════════════════════════════════════════════════

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
        socketio.start_background_task(socketio.emit, event, data, namespace="/")
    except Exception as e:
        print(f"[WS] Broadcast Error: {e}")


# ═══════════════════════════════════════════════════════════════════
# PHẦN 3 – Thay thế endpoint /ask (thêm profile support)
# ═══════════════════════════════════════════════════════════════════

@app.route("/ask", methods=["POST"])
def ask():
    """
    Nhận câu hỏi + profile JSON từ iOS/Extension.
    Trả về gợi ý trả lời tiếng Anh phù hợp với background của ứng viên.

    Body JSON:
    {
        "question": "...",
        "profile": {
            "name": "...",
            "target_roles": [...],
            "skills": {...},
            "projects": [...],
            "experience": "...",
            "background": "..."
        }
    }
    """
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    profile  = data.get("profile", {})

    if not question:
        return jsonify({"error": "Thiếu trường 'question'"}), 400

    # Build profile context block
    profile_block = ""
    if profile:
        skills_data = profile.get("skills", {})
        skills_flat = []
        if isinstance(skills_data, dict):
            for v in skills_data.values():
                if isinstance(v, list):
                    skills_flat.extend(v)
                elif isinstance(v, str):
                    skills_flat.append(v)
        else:
            skills_flat = skills_data if isinstance(skills_data, list) else []

        projects = profile.get("projects", [])
        proj_names = [p.get("name", "") if isinstance(p, dict) else str(p) for p in projects[:4]]

        profile_block = (
            f"\n=== CANDIDATE PROFILE ===\n"
            f"Name: {profile.get('name', 'N/A')}\n"
            f"Target roles: {', '.join(profile.get('target_roles', []))}\n"
            f"Key skills: {', '.join(skills_flat[:12])}\n"
            f"Key projects: {', '.join(proj_names)}\n"
            f"Experience: {profile.get('experience', '')}\n"
            f"Background: {profile.get('background', '')}\n"
            f"Japanese: {profile.get('japanese_level', '')}\n"
            f"=========================\n"
        )

    prompt = (
        "You are an expert interview coach helping a candidate answer live interview questions.\n"
        "Reply ONLY with the suggested answer — no intro, no labels, no markdown headers.\n"
        "Use 2–3 short bullet points starting with '•'.\n"
        "Max 50 words total. Be confident, specific, and tailor the answer to the candidate's real experience.\n"
        "Reference specific projects or skills from the profile when relevant.\n"
        f"{profile_block}\n"
        f"Interviewer's question: {question}\n"
        "Suggested answer (English, bullet points):"
    )

    try:
        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=150,
                temperature=0.35,
            ),
        )
        suggestion = response.text.strip()
        print(f"[Gemini/Ask] {question[:50]}... → {len(suggestion)} chars")
        return jsonify({"suggestion": suggestion})

    except Exception as e:
        print(f"[Gemini Error] {e}")
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# PHẦN 4 – 2 endpoint mới: /poll và /summarize
# Thêm vào trước endpoint /health
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
    Tóm tắt câu hỏi dài bằng tiếng Việt ngắn gọn.
    Dùng khi transcript > 30 words → iOS tự động gọi endpoint này.

    Body JSON: { "text": "...(long English question)..." }
    Response:  { "summary_vi": "...(tóm tắt tiếng Việt)..." }
    """
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "Thiếu trường 'text'"}), 400

    prompt = (
        "Summarize this English interview question in Vietnamese.\n"
        "Rules:\n"
        "- Vietnamese only\n"
        "- Max 20 words\n"
        "- Keep the core question meaning\n"
        "- No intro, no labels, just the summary\n\n"
        f"Question: {text}\n"
        "Tóm tắt tiếng Việt:"
    )

    try:
        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=60,
                temperature=0.2,
            ),
        )
        summary_vi = response.text.strip()
        print(f"[Gemini/Sum] {text[:40]}... → {summary_vi[:40]}")
        return jsonify({"summary_vi": summary_vi})

    except Exception as e:
        print(f"[Gemini/Sum Error] {e}")
        return jsonify({"error": str(e)}), 500
