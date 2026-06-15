"""
backend_suggestion_trigger.py
==============================
Cơ chế kích hoạt gợi ý trả lời trên backend.
Tích hợp với ai_suggestion.py để xử lý Gemini + Ollama fallback.

HƯỚNG DẪN TÍCH HỢP:
1. Thêm vào backend.py (line ~30):
   from ai_suggestion import get_suggestion

2. Thêm section này vào backend.py (trước endpoint /health):
   - Tất cả code dưới đây

3. Khởi động:
   - ollama serve (terminal 1)
   - python backend.py (terminal 2)
   
4. iOS sẽ tự động gọi /ask khi nhấn Ctrl+Shift+Z
"""

import json
import time
import threading
from flask import request, jsonify
from flask_socketio import emit

# ═══════════════════════════════════════════════════════════════════════════
# STATE TRACKING: Suggestion requests & results
# ═══════════════════════════════════════════════════════════════════════════

_suggestion_in_progress = False
_last_suggestion = ""
_last_suggestion_source = ""
_suggestion_timestamp = 0

_suggestion_lock = threading.Lock()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENDPOINT: POST /ask
# Triggered by iOS keyboard shortcut (Ctrl+Shift+Z)
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/ask", methods=["POST"])
def ask():
    """
    🎯 SUGGESTION TRIGGER ENDPOINT
    
    Nhận câu hỏi + profile từ iOS (khi nhấn Ctrl+Shift+Z).
    Trả về gợi ý trả lời AI dựa trên CandidateProfile.
    
    🔄 Fallback Logic:
    1. Try Gemini Cloud (primary)
    2. Fallback to Ollama Local (if available)
    3. Return error with setup instructions

    Request JSON (from iOS):
    {
        "question": "Tell me about your AI experience",
        "profile": {
            "name": "Lê Đăng Khoa",
            "target_roles": ["AI Full Stack Engineer"],
            "skills": {
                "languages": ["Python", "Swift"],
                "frameworks": ["FastAPI", "SwiftUI"],
                "ai_tools": ["Gemini API", "Ollama"],
                "infra": ["Docker", "PostgreSQL"]
            },
            "projects": [
                {"name": "PentaSchool", "desc": "..."},
                {"name": "PentaMO", "desc": "..."}
            ],
            "experience": "Self-taught developer",
            "background": "Transitioning from manufacturing",
            "japanese_level": "JLPT N3"
        }
    }

    Response JSON:
    {
        "success": true,
        "suggestion": "• Developed AI pipelines using...",
        "source": "gemini",  # or "ollama", "cache", "error"
        "processing_time": 1.234
    }
    """
    global _suggestion_in_progress, _last_suggestion, _last_suggestion_source, _suggestion_timestamp

    start_time = time.time()

    # ─── Parse request ───────────────────────────────────────────────────
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    profile = data.get("profile", {})

    if not question:
        return jsonify({
            "success": False,
            "error": "Missing 'question' field",
            "suggestion": ""
        }), 400

    # ─── Prevent concurrent requests ─────────────────────────────────────
    with _suggestion_lock:
        if _suggestion_in_progress:
            return jsonify({
                "success": False,
                "error": "Suggestion already in progress, please wait...",
                "suggestion": ""
            }), 429  # Too Many Requests

        _suggestion_in_progress = True
        _broadcast_event("suggestion_start", {
            "question": question,
            "processing": True
        })

    try:
        print(f"\n[Ask] Received: {question[:60]}...")
        print(f"[Ask] Profile: {profile.get('name', 'Unknown')}")

        # ─── Call ai_suggestion module with fallback ─────────────────────
        result = get_suggestion(question, profile)

        processing_time = time.time() - start_time

        # ─── Success case ───────────────────────────────────────────────
        if result["success"]:
            suggestion = result["suggestion"]
            source = result["source"]

            with _suggestion_lock:
                _last_suggestion = suggestion
                _last_suggestion_source = source
                _suggestion_timestamp = time.time()

            response = {
                "success": True,
                "suggestion": suggestion,
                "source": source,  # "gemini", "ollama", "cache"
                "processing_time": round(processing_time, 3)
            }

            print(f"[Ask] ✓ Success ({source}) in {processing_time:.2f}s")
            print(f"      Suggestion: {suggestion[:80]}...")

            # Broadcast via WebSocket for real-time UI update
            _broadcast_event("suggestion", response)

            return jsonify(response), 200

        # ─── Error case ─────────────────────────────────────────────────
        else:
            error_msg = result["suggestion"]  # Error message
            response = {
                "success": False,
                "error": error_msg,
                "suggestion": "",
                "source": "error",
                "processing_time": round(processing_time, 3)
            }

            print(f"[Ask] ✗ Failed: {error_msg[:60]}...")

            _broadcast_event("suggestion_error", response)

            return jsonify(response), 503  # Service Unavailable

    except Exception as e:
        error_msg = f"Backend error: {str(e)}"
        print(f"[Ask] ✗ Exception: {error_msg}")

        response = {
            "success": False,
            "error": error_msg,
            "suggestion": "",
            "source": "error"
        }

        _broadcast_event("suggestion_error", response)

        return jsonify(response), 500

    finally:
        with _suggestion_lock:
            _suggestion_in_progress = False
            _broadcast_event("suggestion_done", {
                "success": result.get("success", False) if "result" in locals() else False
            })


# ═══════════════════════════════════════════════════════════════════════════
# HELPER ENDPOINT: GET /suggestion/status
# iOS can poll for current suggestion status
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/suggestion/status", methods=["GET"])
def suggestion_status():
    """
    Kiểm tra trạng thái gợi ý hiện tại.
    iOS có thể dùng để biết suggestion có sẵn chưa.

    Response:
    {
        "in_progress": false,
        "has_suggestion": true,
        "last_suggestion": "• Developed AI...",
        "source": "gemini",
        "timestamp": 1234567890.123
    }
    """
    with _suggestion_lock:
        return jsonify({
            "in_progress": _suggestion_in_progress,
            "has_suggestion": len(_last_suggestion) > 0,
            "last_suggestion": _last_suggestion,
            "source": _last_suggestion_source,
            "timestamp": _suggestion_timestamp
        }), 200


# ═══════════════════════════════════════════════════════════════════════════
# HELPER ENDPOINT: DELETE /suggestion/clear
# Clear cached suggestion
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/suggestion/clear", methods=["DELETE"])
def suggestion_clear():
    """
    Xoá cached suggestion (nếu muốn fetch mới).
    iOS có thể gọi nếu muốn buộc refresh.
    """
    global _last_suggestion, _last_suggestion_source, _suggestion_timestamp

    with _suggestion_lock:
        _last_suggestion = ""
        _last_suggestion_source = ""
        _suggestion_timestamp = 0

    _broadcast_event("suggestion_cleared", {})

    return jsonify({"success": True, "message": "Suggestion cleared"}), 200


# ═══════════════════════════════════════════════════════════════════════════
# WEBSOCKET EVENTS (Real-time broadcast to iOS/Extension)
# ═══════════════════════════════════════════════════════════════════════════

def _broadcast_event(event_type: str, data: dict):
    """
    Broadcast suggestion events via WebSocket (iOS polling).
    Events: suggestion_start, suggestion, suggestion_error, suggestion_done
    """
    try:
        event_data = {
            "type": event_type,
            "data": data,
            "ts": time.time()
        }

        # Log event
        _log_event(event_type, data)

        # Broadcast via Socket.IO (for Chrome Extension)
        socketio.start_background_task(
            socketio.emit,
            event_type,
            event_data,
            namespace="/"
        )

        print(f"[WS] Broadcast {event_type}: {str(data)[:80]}...")

    except Exception as e:
        print(f"[WS] Broadcast Error ({event_type}): {e}")


# ═══════════════════════════════════════════════════════════════════════════
# DEBUG/TEST ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/ask/test", methods=["POST"])
def ask_test():
    """
    Test endpoint (for debugging without iOS).
    POST with same JSON format as /ask.

    Example curl:
    curl -X POST http://localhost:5000/ask/test \\
      -H "Content-Type: application/json" \\
      -d '{
        "question": "Tell me about your strongest project",
        "profile": {
          "name": "Test User",
          "target_roles": ["Engineer"],
          "skills": {"languages": ["Python"]},
          "projects": [],
          "experience": "Testing",
          "background": "Test",
          "japanese_level": "N3"
        }
      }'
    """
    return ask()  # Same logic as /ask


@app.route("/ask/mock", methods=["GET"])
def ask_mock():
    """
    Mock response (no AI call, just returns sample).
    Useful for UI testing.
    """
    return jsonify({
        "success": True,
        "suggestion": "• Developed AI pipelines using Gemini API and Ollama\n• Built FastAPI servers with real-time STT/LLM/TTS\n• Specialized in local-first AI systems and multi-platform deployment",
        "source": "mock",
        "processing_time": 0.1
    }), 200


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATION CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════

"""
☐ Step 1: Add import (line ~30 in backend.py)
   from ai_suggestion import get_suggestion

☐ Step 2: Copy all code from this file into backend.py
   (before endpoint /health)

☐ Step 3: Verify ai_suggestion.py is in same directory

☐ Step 4: Install dependencies
   pip install -r requirements.txt

☐ Step 5: Setup Ollama (optional but recommended)
   ollama pull llama3.2
   ollama serve  (keep running)

☐ Step 6: Start backend
   export GEMINI_API_KEY="your_key"  (optional)
   python backend.py

☐ Step 7: Test endpoints
   # Health checks
   curl -X GET http://localhost:5000/health/gemini
   curl -X GET http://localhost:5000/health/ollama

   # Test suggestion
   curl -X GET http://localhost:5000/ask/mock
   curl -X POST http://localhost:5000/ask/test -d '{...}'

   # Check status
   curl -X GET http://localhost:5000/suggestion/status

☐ Step 8: Update iOS BackendService.swift
   - askForSuggestion() should POST to /ask
   - Include CandidateProfile.current.asDict
   - Handle response with source indicator

☐ Step 9: iOS keyboard shortcut
   - Ctrl+Shift+Z now triggers askForSuggestion()
   - Backend processes and returns suggestion
   - iOS displays in "Gợi ý" panel

✅ DONE! Ready to use
"""

# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

"""
MAIN ENDPOINTS:
───────────────
POST   /ask                    → Get suggestion (triggered by iOS Ctrl+Shift+Z)
GET    /suggestion/status      → Check suggestion status
DELETE /suggestion/clear       → Clear cached suggestion

DEBUG ENDPOINTS:
────────────────
POST   /ask/test               → Test /ask endpoint (debugging)
GET    /ask/mock               → Mock response (UI testing)

EXISTING ENDPOINTS (from backend.py):
──────────────────────────────────────
GET    /health                 → Server status
GET    /health/gemini          → Gemini API status
GET    /health/ollama          → Ollama server status
POST   /poll                   → iOS polling
POST   /poll/clear             → Clear iOS poll cache
WS     /                       → WebSocket connection


FULL FLOW:
──────────
1. iOS user presses Ctrl+Shift+Z
2. iOS calls POST /ask with question + profile
3. Backend receives request
4. ai_suggestion.get_suggestion() processes:
   a. Check cache → return if found
   b. Try Gemini Cloud → success? return + cache
   c. Try Ollama Local → success? return + cache
   d. Both failed? return error
5. Backend returns JSON response
6. iOS receives suggestion
7. Shows in "Gợi ý trả lời" panel with source indicator
8. User reads AI suggestion
9. User answers interviewer with suggested answer
10. Interview continues...
"""
