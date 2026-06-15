# 🚀 QUICK START: AI Suggestion với Ollama Fallback

## 📋 Overview
Hệ thống gợi ý câu trả lời phỏng vấn dựa trên **CandidateProfile**:
- ✅ **Primary**: Gemini Cloud (nhanh, chính xác)
- ✅ **Fallback**: Ollama Local Llama3.2 (offline, tự do)
- ✅ **Cache**: Tránh API call duplicate
- ✅ **Smart Profile Context**: Tối ưu câu trả lời dựa trên kinh nghiệm

---

## ⚡ 3-Minute Setup

### 1️⃣ Install Dependencies
```bash
cd /Users/gooleseswsq1gmail.com/Documents/Pentainterview
pip install -r requirements.txt
```

### 2️⃣ Setup Ollama (Fallback LLM)
```bash
# Install Ollama
brew install ollama

# Pull model (~5GB, chạy 1 lần)
ollama pull llama3.2

# Start server (giữ terminal này mở)
ollama serve
```

**Output:**
```
2024-05-03 10:00:00 listening on 127.0.0.1:11434
```

✅ Ollama ready on `http://localhost:11434`

### 3️⃣ Setup Gemini API (Optional)
```bash
# Get API key: https://aistudio.google.com
export GEMINI_API_KEY="your_api_key_here"
```

*Lưu ý: Nếu không setup, hệ thống fallback sang Ollama tự động*

### 4️⃣ Test Module
```bash
# Terminal mới (Ollama vẫn chạy ở terminal trước)
python ai_suggestion.py
```

**Expected Output:**
```
======================================================================
AI SUGGESTION MODULE TEST
======================================================================

📌 Question: Tell me about your AI experience
   Source: gemini   # hoặc "ollama" nếu Gemini không available
   Suggestion:
   • Developed AI pipelines using Gemini API and Ollama
   • Built FastAPI servers with real-time STT/LLM/TTS integration
   • Specialized in local-first AI systems and multi-platform deployment
```

✅ Đã test thành công!

---

## 🔌 Integrate vào Backend

### Option A: Auto-Integrate (Recommended)
```bash
# Backup original
cp backend.py backend.py.bak

# Copy updated endpoint
# Mở backend_ask_endpoint_updated.py, copy hàm @app.route("/ask")
# Paste vào backend.py thay thế hàm /ask cũ

# Thêm import (nếu chưa có):
# from ai_suggestion import get_suggestion
```

### Option B: Manual Integration
1. **Thêm import** (line ~30 trong backend.py):
   ```python
   from ai_suggestion import get_suggestion
   ```

2. **Thay thế hàm** `/ask` bằng code từ `backend_ask_endpoint_updated.py`

3. **Verify**:
   ```bash
   python -m py_compile backend.py  # Check syntax
   ```

---

## 🧪 Test Backend Integration

### Terminal Setup
```bash
# Terminal 1: Ollama server
ollama serve

# Terminal 2: Backend server
export GEMINI_API_KEY="your_key"  # Optional
python backend.py

# Terminal 3: Test (chạy sau 2-3s)
```

### Health Checks
```bash
# Check Gemini API
curl -X GET http://localhost:5000/health/gemini
# Response: {"status": "ok"} hoặc {"status": "not_configured"}

# Check Ollama
curl -X GET http://localhost:5000/health/ollama
# Response: {"status": "ok", "models": ["llama3.2"]}
```

### Test /ask Endpoint
```bash
curl -X POST http://localhost:5000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Tell me about your strongest project",
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
        {"name": "PentaSchool", "desc": "LMS with AI auto-grading"},
        {"name": "PentaMO", "desc": "AI motorcycle marketplace"}
      ],
      "experience": "Self-taught full-stack developer, JLPT N3",
      "background": "Transitioned from manufacturing to software",
      "japanese_level": "JLPT N3"
    }
  }'
```

**Expected Response:**
```json
{
  "suggestion": "• PentaSchool: Full-stack LMS with AI auto-grading, KaTeX rendering, Vietnamese K12 exam support\n• PentaMO: AI marketplace with semantic caching via FAISS and local Ollama inference\n• Both demonstrate full-stack architecture: React/Next.js frontend, FastAPI backend, multi-language support",
  "source": "gemini"
}
```

✅ Thành công!

---

## 📊 Performance Expectations

| Source | Time | Cost | Reliability |
|--------|------|------|-------------|
| **Cache** | <100ms | Free | 100% |
| **Gemini Cloud** | 1-3s | API quota | ~99% |
| **Ollama Local** | 2-5s | Free | 100% |
| **Error** | <100ms | Free | 0% |

**Scenario 1: Gemini available**
```
1. User asks question (1s)
   ↓
2. Try cache → miss
   ↓
3. Call Gemini Cloud → success (1-3s)
4. Cache result
5. Return to client
═════════════════════════════════════
Total: ~2-4s
```

**Scenario 2: Gemini fails, Ollama available**
```
1. User asks question
   ↓
2. Try cache → miss
   ↓
3. Call Gemini Cloud → timeout/error (1-2s)
   ↓
4. Fallback to Ollama Local → success (2-5s)
5. Cache result
6. Return to client
═════════════════════════════════════
Total: ~3-7s (still acceptable for interview prep)
```

**Scenario 3: Both offline**
```
1. User asks question
   ↓
2. Try cache → miss
   ↓
3. Call Gemini → fail
4. Call Ollama → fail
5. Return error message with setup instructions
═════════════════════════════════════
Total: ~1-2s + helpful error message
```

---

## 🎯 Usage Examples

### From iOS SwiftUI
```swift
// Build request with CandidateProfile
let profile = CandidateProfile.current.asDict
let request = [
    "question": "What's your experience with AI systems?",
    "profile": profile
] as [String: Any]

// POST to /ask endpoint
URLSession.shared.dataTask(with: url, from: request) { data, _, error in
    if let suggestion = try? JSONDecoder().decode([String: String].self, from: data!) {
        print(suggestion["suggestion"])  // Display to user
    }
}.resume()
```

### From Chrome Extension
```javascript
// popup.js
async function askAI(question, profile) {
    const response = await fetch('http://localhost:5000/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, profile })
    });
    
    const data = await response.json();
    console.log('Suggestion:', data.suggestion);
    console.log('Source:', data.source);  // "gemini", "ollama", or "cache"
}
```

---

## 🛠️ Troubleshooting

### ❌ "Connection refused: Ollama"
```
[Ollama] ✗ Connection failed - Server not running?
```
**Fix:**
```bash
# Terminal 1
ollama serve
```

### ❌ "Gemini 401 Unauthorized"
**Fix:**
```bash
export GEMINI_API_KEY="your_valid_key"
python backend.py
```

### ❌ "Ollama model not found"
**Fix:**
```bash
ollama pull llama3.2
ollama list  # verify
```

### ❌ Slow responses (>10s)
**Cause:** Ollama running on CPU
**Solutions:**
1. Use GPU if available
2. Try lighter model: `ollama pull mistral`
3. Check system resources: `top` or Activity Monitor
4. Make sure Ollama not running multiple inferences

### ⚠️ "ModuleNotFoundError: ai_suggestion"
**Fix:**
- Ensure `ai_suggestion.py` is in same directory as `backend.py`
- OR add to backend.py:
  ```python
  import sys
  sys.path.insert(0, '/Users/gooleseswsq1gmail.com/Documents/Pentainterview')
  ```

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `ai_suggestion.py` | Core module (Gemini + Ollama + fallback) |
| `backend_ask_endpoint_updated.py` | Updated `/ask` endpoint with health checks |
| `INTEGRATION_GUIDE.md` | Detailed integration & configuration |
| `QUICK_START.md` | This file (quick reference) |

---

## 🚀 Next Steps

1. **Run 3-minute setup** (above) ✅
2. **Test `ai_suggestion.py`** to verify both sources work
3. **Integrate into `backend.py`** using `backend_ask_endpoint_updated.py`
4. **Test `/ask` endpoint** with curl or Postman
5. **Use from iOS/Extension** - no changes needed!

---

## 💡 Pro Tips

### Optimize for Performance
```bash
# Use lighter Ollama model for faster responses
ollama pull mistral  # ~7B, faster than llama3.2

# Update ai_suggestion.py:
OLLAMA_MODEL = "mistral"
```

### Optimize for Quality
```bash
# Use larger model for better answers
ollama pull neural-chat  # Optimized for conversation

# Update ai_suggestion.py:
OLLAMA_MODEL = "neural-chat"
```

### Monitor & Debug
```bash
# Check Gemini API quota
curl -X GET http://localhost:5000/health/gemini

# Check Ollama models
curl -X GET http://localhost:5000/health/ollama

# Watch backend logs
tail -f <backend_output.log>
```

---

## 📞 Support

**问题?** Check:
1. INTEGRATION_GUIDE.md (detailed guide)
2. backend_ask_endpoint_updated.py (code template)
3. Logs from `ollama serve` and `python backend.py`
4. Health endpoints: `/health/ollama`, `/health/gemini`

Good luck! 🎉
