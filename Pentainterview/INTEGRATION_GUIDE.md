# Integration Guide: AI Suggestion with Ollama Fallback

## Overview
Tích hợp module `ai_suggestion.py` vào backend để:
- **Primary**: Dùng Gemini Cloud để generate gợi ý câu trả lời
- **Fallback**: Nếu Gemini fail, tự động chuyển sang Ollama Local (Llama3.2)
- **Cache**: Tránh duplicate API calls

## Prerequisites

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Ollama (Fallback Local LLM)

#### macOS
```bash
# Install via Homebrew
brew install ollama

# Pull Llama3.2 model (~5GB)
ollama pull llama3.2

# Start Ollama server (giữ terminal này chạy)
ollama serve
```

**Lưu ý**: Server sẽ chạy ở `http://localhost:11434`

#### Linux / Windows
Xem: https://ollama.ai

### 3. Setup Gemini API (Optional nhưng recommended)
```bash
export GEMINI_API_KEY="your_api_key_here"
```

Nếu không setup, hệ thống sẽ fallback sang Ollama ngay lập tức.

---

## Integration Steps

### Step 1: Thêm import vào backend.py
Thêm dòng này ở phần import (khoảng line 30):
```python
from ai_suggestion import get_suggestion
```

### Step 2: Thay thế endpoint `/ask`

**Tìm hàm này trong backend.py:**
```python
@app.route("/ask", methods=["POST"])
def ask():
    """
    Nhận câu hỏi + profile JSON từ iOS/Extension.
    Trả về gợi ý trả lời...
    """
```

**Thay thế toàn bộ hàm bằng:**
```python
@app.route("/ask", methods=["POST"])
def ask():
    """
    Nhận câu hỏi + profile JSON từ iOS/Extension.
    Trả về gợi ý trả lời tiếng Anh phù hợp với background của ứng viên.
    
    Fallback: Gemini Cloud → Ollama Local (Llama3.2)

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

    # Use ai_suggestion module with fallback
    result = get_suggestion(question, profile)
    
    if result["success"]:
        return jsonify({
            "suggestion": result["suggestion"],
            "source": result["source"]  # "gemini", "ollama", or "cache"
        })
    else:
        return jsonify({
            "error": result["suggestion"],
            "source": "error"
        }), 503
```

### Step 3: (Optional) Cập nhật iOS/Extension code
Phía client không thay đổi gì, vẫn gọi `/ask` như bình thường.

---

## How It Works

### 1️⃣ Request đến
```json
{
    "question": "Tell me about your AI experience",
    "profile": {
        "name": "Lê Đăng Khoa",
        "target_roles": ["AI Full Stack Engineer"],
        "skills": {...},
        ...
    }
}
```

### 2️⃣ Processing Flow
```
get_suggestion() {
    1. Check cache → return if found
    2. Try Gemini Cloud
       ├─ Success? → cache + return
       └─ Fail? → continue
    3. Try Ollama Local (Llama3.2)
       ├─ Success? → cache + return
       └─ Fail? → return error
}
```

### 3️⃣ Response từ
```json
{
    "suggestion": "• Developed AI pipelines using Gemini API and Ollama\n• Built FastAPI servers with real-time STT/LLM/TTS\n• Integrated FAISS vector search for semantic caching",
    "source": "gemini"  // or "ollama", "cache", "error"
}
```

---

## Testing

### 1. Test AI Suggestion Module Directly
```bash
python ai_suggestion.py
```

Output:
```
======================================================================
AI SUGGESTION MODULE TEST
======================================================================

📌 Question: Tell me about your AI experience
   Source: gemini  (hoặc ollama, cache, error)
   Suggestion:
   • Developed AI pipelines using Gemini API and Ollama
   • Built FastAPI servers with real-time STT/LLM/TTS
   • Integrated FAISS vector search for semantic caching

...
```

### 2. Test via Backend
```bash
# Start Ollama (terminal 1)
ollama serve

# Start backend (terminal 2)
export GEMINI_API_KEY="your_key"
python backend.py

# Test with curl (terminal 3)
curl -X POST http://localhost:5000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is your strongest project?",
    "profile": {
      "name": "Lê Đăng Khoa",
      "target_roles": ["AI Full Stack Engineer"],
      "skills": {
        "languages": ["Python", "Swift"],
        "frameworks": ["FastAPI", "SwiftUI"],
        "ai_tools": ["Gemini", "Ollama"],
        "infra": ["Docker", "Vercel"]
      },
      "projects": [
        {"name": "PentaSchool", "desc": "LMS with AI auto-grading"},
        {"name": "PentaMO", "desc": "AI motorcycle marketplace"}
      ],
      "experience": "Self-taught developer",
      "background": "Transitioning from manufacturing",
      "japanese_level": "JLPT N3"
    }
  }'
```

Expected response:
```json
{
  "suggestion": "• PentaSchool: Full LMS with AI auto-grading and KaTeX rendering\n• PentaMO: AI marketplace with FAISS semantic cache and Ollama inference\n• Both showcase full-stack skills from Python backend to SwiftUI frontend",
  "source": "gemini"
}
```

---

## Configuration

### Environment Variables
```bash
# Optional: Set custom Ollama server URL
export OLLAMA_BASE_URL="http://localhost:11434"

# Optional: Set Gemini API key
export GEMINI_API_KEY="your_key"

# Optional: Ollama model (default: llama3.2)
# Supported: llama3.2, mistral, neural-chat, etc.
```

### Rate Limiting
- **Gemini**: Max 10 calls/hour (conservative limit)
- **Ollama**: Unlimited (local, no API quota)
- **Cache**: All successful responses are cached

---

## Troubleshooting

### ❌ "Ollama Connection failed"
```
[Ollama] ✗ Connection failed - Server not running?
         Start with: ollama serve
```
**Solution:**
1. Open new terminal
2. Run: `ollama serve`
3. Keep it running in background

### ❌ "Gemini error: 401 Unauthorized"
```
[Gemini] Error: 401 Invalid API key
```
**Solution:**
1. Check: `echo $GEMINI_API_KEY`
2. Get key from: https://aistudio.google.com
3. Set: `export GEMINI_API_KEY="..."`

### ❌ "No module named 'requests'"
```
ModuleNotFoundError: No module named 'requests'
```
**Solution:**
```bash
pip install requests
# hoặc
pip install -r requirements.txt
```

### ⚠️ Both Gemini AND Ollama failed
Response sẽ là error message với hướng dẫn fix. Check logs để xác định vấn đề.

---

## Performance Notes

### Response Times
- **Gemini**: 1-3 seconds (network + cloud processing)
- **Ollama (Llama3.2)**: 2-5 seconds (local processing, depends on hardware)
- **Cache**: <100ms

### Hardware Requirements for Ollama
- **Minimum**: 4GB RAM, M1 Mac tốt
- **Recommended**: 8GB+ RAM, M1/M2+ Mac, NVidia GPU

### Model Alternatives
If Llama3.2 không phù hợp:
```bash
ollama pull mistral          # Nhẹ hơn, nhanh hơn (~7B params)
ollama pull neural-chat      # Optimized cho chat (~7B params)
ollama pull dolphin-mixtral  # Cao cấp hơn (~8x7B params)
```

Cập nhật `OLLAMA_MODEL` trong `ai_suggestion.py`:
```python
OLLAMA_MODEL = "mistral"  # thay đổi từ "llama3.2"
```

---

## Deployment Notes

### Production (nếu chạy trên server)
1. **Gemini** sẽ là primary (fast, reliable)
2. **Ollama** tối ưu cho fallback hoặc offline mode
3. Nên setup **Docker** để standardize environment:

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "backend.py"]
```

### Monitoring
Logs sẽ show:
- `[Gemini] ✓ Generated suggestion` → Cloud API used
- `[Ollama] ✓ Generated suggestion [LOCAL]` → Local fallback used
- `[Cache] ✓ Hit!` → Cached response used
- `[Gemini] Error:` → Fallback triggered

---

## Summary
✅ Gợi ý câu trả lời có fallback mechanism
✅ Tự động fallback từ Gemini → Ollama khi cloud fail
✅ Caching để tối ưu response time
✅ Dễ test, dễ deploy, dễ configure

**Start with:**
```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: Backend
export GEMINI_API_KEY="your_key"
python backend.py

# Terminal 3: Test
python ai_suggestion.py
```
