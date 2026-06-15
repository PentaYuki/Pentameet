"""
backend_updated_ask_endpoint.py
===============================
Updated /ask endpoint sử dụng ai_suggestion module với fallback.

HƯỚNG DẪN:
1. Thêm import vào backend.py (line ~30):
   from ai_suggestion import get_suggestion

2. Thay thế toàn bộ hàm /ask bằng code dưới đây

3. Run:
   ollama serve  (terminal 1, để background)
   python backend.py  (terminal 2)
"""

# ════════════════════════════════════════════════════════════════════════════
# COPY THIS ENTIRE FUNCTION INTO backend.py
# ════════════════════════════════════════════════════════════════════════════

@app.route("/ask", methods=["POST"])
def ask():
    """
    Nhận câu hỏi + profile JSON từ iOS/Extension.
    Trả về gợi ý trả lời tiếng Anh phù hợp với background của ứng viên.
    
    🔄 Fallback Logic: Gemini Cloud → Ollama Local (Llama3.2) → Error

    Request Body JSON:
    {
        "question": "Tell me about your AI experience",
        "profile": {
            "name": "Lê Đăng Khoa",
            "target_roles": ["AI Full Stack Engineer", "Bridge Software Engineer"],
            "skills": {
                "languages": ["Python", "Swift", "JavaScript"],
                "frameworks": ["FastAPI", "SwiftUI", "React"],
                "ai_tools": ["Gemini API", "Ollama", "LangChain"],
                "infra": ["Docker", "PostgreSQL", "Vercel"]
            },
            "projects": [
                {"name": "PentaSchool (LMS)", "desc": "..."},
                {"name": "PentaMO (AI Marketplace)", "desc": "..."}
            ],
            "experience": "Self-taught developer, JLPT N3",
            "background": "Transitioning from manufacturing...",
            "japanese_level": "JLPT N3 (studying N2)"
        }
    }

    Response JSON:
    {
        "suggestion": "• Developed AI pipelines using...\n• Built FastAPI servers...",
        "source": "gemini"  // "gemini", "ollama", "cache", or error
    }
    """
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    profile  = data.get("profile", {})

    # Validate input
    if not question:
        return jsonify({"error": "Thiếu trường 'question'"}), 400

    print(f"\n[Ask] Q: {question[:60]}...")
    print(f"      Profile: {profile.get('name', 'N/A')}")

    # ─── Use ai_suggestion module with fallback ───────────────────────────
    result = get_suggestion(question, profile)
    
    if result["success"]:
        response = {
            "suggestion": result["suggestion"],
            "source": result["source"]  # Debugging info: where did this come from?
        }
        print(f"[Ask] ✓ Success ({result['source']})")
        return jsonify(response), 200
    else:
        # Both Gemini AND Ollama failed
        response = {
            "error": result["suggestion"],
            "source": "error"
        }
        print(f"[Ask] ✗ Failed - returning error message")
        return jsonify(response), 503


# ════════════════════════════════════════════════════════════════════════════
# OPTIONAL: Extra endpoints for debugging
# ════════════════════════════════════════════════════════════════════════════

@app.route("/health/ollama", methods=["GET"])
def health_ollama():
    """
    Kiểm tra xem Ollama server có chạy không.
    GET /health/ollama
    """
    try:
        response = requests.get(f"{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return jsonify({
                "status": "ok",
                "message": f"Ollama running with {len(models)} models",
                "models": [m.get("name") for m in models]
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": f"Ollama returned {response.status_code}"
            }), 502
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Ollama not available: {str(e)}"
        }), 503


@app.route("/health/gemini", methods=["GET"])
def health_gemini():
    """
    Kiểm tra xem Gemini API có khả dụng không.
    GET /health/gemini
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    if not api_key:
        return jsonify({
            "status": "not_configured",
            "message": "GEMINI_API_KEY not set"
        }), 200
    
    try:
        # Try a simple API call
        import google.genai as genai
        genai.configure(api_key=api_key)
        
        # List models just to verify API key works
        models = genai.list_models()
        return jsonify({
            "status": "ok",
            "message": f"Gemini API available ({len(list(models))} models)"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Gemini API error: {str(e)}"
        }), 502


# ════════════════════════════════════════════════════════════════════════════
# INTEGRATION CHECKLIST
# ════════════════════════════════════════════════════════════════════════════

"""
☐ Step 1: Thêm import
   from ai_suggestion import get_suggestion
   
☐ Step 2: Thêm requests import (nếu chưa có)
   import requests
   
☐ Step 3: Copy /ask endpoint mới từ file này vào backend.py
   (Replace toàn bộ hàm @app.route("/ask", methods=["POST"]))
   
☐ Step 4: (Optional) Thêm 2 health check endpoints
   (/health/ollama, /health/gemini)
   
☐ Step 5: Cài dependencies
   pip install -r requirements.txt
   
☐ Step 6: Setup Ollama
   ollama pull llama3.2
   ollama serve  (chạy ở terminal khác)
   
☐ Step 7: Test
   # Terminal 3
   curl -X GET http://localhost:5000/health/gemini
   curl -X GET http://localhost:5000/health/ollama
   
   curl -X POST http://localhost:5000/ask \\
     -H "Content-Type: application/json" \\
     -d '{
       "question": "What is your strongest project?",
       "profile": {...}
     }'
"""

# ════════════════════════════════════════════════════════════════════════════
# TROUBLESHOOTING
# ════════════════════════════════════════════════════════════════════════════

"""
Problem: "ModuleNotFoundError: No module named 'ai_suggestion'"
Solution: Make sure ai_suggestion.py is in the same directory as backend.py
          or add path: sys.path.insert(0, '/path/to/pentainterview')

Problem: "Connection refused: Ollama"
Solution: Start Ollama in another terminal:
          ollama serve
          (keep it running)

Problem: "GEMINI_API_KEY not set"
Solution: Run before starting backend:
          export GEMINI_API_KEY="your_api_key"
          python backend.py

Problem: "Ollama model not found"
Solution: Pull the model first:
          ollama pull llama3.2
          ollama list  (verify)

Problem: Slow response times
Solution: Ollama processes locally, may take 2-5s on CPU
          - Use GPU if available
          - Try lighter model: ollama pull mistral
          - Check system resources: top, Activity Monitor
"""
