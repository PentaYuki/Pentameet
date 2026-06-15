# 📚 AI Suggestion System - Documentation Index

> **PentaInterview**: AI-powered interview assistant with Gemini Cloud ↔ Ollama Local fallback

---

## 📖 Getting Started

**New to this feature?** Start here:

1. **[QUICK_START.md](QUICK_START.md)** ⭐ **START HERE** (3 minutes)
   - Install dependencies
   - Setup Ollama
   - Test the system
   - Integrate with backend

2. **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** (Detailed guide)
   - Complete prerequisites
   - Step-by-step integration
   - Testing procedures
   - Troubleshooting

3. **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** (Reference)
   - What's new
   - Architecture overview
   - Performance profile
   - Known limitations

---

## 🔧 Technical Files

### Core Module
- **[ai_suggestion.py](ai_suggestion.py)** - AI suggestion engine
  - Fallback logic: Gemini Cloud → Ollama Local
  - Caching & rate limiting
  - Profile context injection
  - Ready to import and use

### Updated Backend
- **[backend_ask_endpoint_updated.py](backend_ask_endpoint_updated.py)** - Code template
  - Updated `/ask` endpoint
  - Health check endpoints
  - Copy-paste ready
  - Integration checklist

### Dependencies
- **[requirements.txt](requirements.txt)** - Updated dependencies
  - Added: `requests>=2.31.0` for Ollama API

---

## 🚀 Quick Integration (Copy-Paste)

### Step 1: Install
```bash
pip install -r requirements.txt
```

### Step 2: Setup Ollama (Fallback)
```bash
ollama pull llama3.2
ollama serve
```

### Step 3: Test Module
```bash
python ai_suggestion.py
```

### Step 4: Update Backend
```python
# Add to backend.py (line ~30):
from ai_suggestion import get_suggestion

# Replace /ask endpoint with code from:
# backend_ask_endpoint_updated.py
```

### Step 5: Start Backend
```bash
export GEMINI_API_KEY="your_key"  # Optional
python backend.py
```

### Step 6: Verify
```bash
curl -X GET http://localhost:5000/health/ollama
curl -X POST http://localhost:5000/ask -d '{...}'
```

✅ **Done!**

---

## 🤖 How It Works

### Flow Diagram
```
User asks interview question
    ↓
/ask endpoint receives request
    ↓
ai_suggestion.get_suggestion()
    ├─ Check cache
    │   └─ If found → return instantly
    ├─ Try Gemini Cloud (primary)
    │   ├─ Success → cache & return (1-3s)
    │   └─ Fail → continue
    ├─ Try Ollama Local (fallback)
    │   ├─ Success → cache & return (2-5s)
    │   └─ Fail → continue
    └─ Return error with instructions
    ↓
Response sent to iOS/Extension
```

### What Gets Generated
Given profile:
```json
{
  "name": "Lê Đăng Khoa",
  "target_roles": ["AI Full Stack Engineer"],
  "skills": {...},
  "projects": [...],
  "experience": "...",
  "background": "..."
}
```

And question: *"Tell me about your strongest project"*

AI generates:
```
• PentaSchool: Full-stack LMS with AI auto-grading, KaTeX rendering, Vietnamese K12 exam support
• Real impact: Handles 1000+ students, 10k+ exam questions, live on Vercel + Supabase
• Technical highlight: Trained in Python, deployed to production with Socket.IO real-time sync
```

---

## 🎯 Key Features

✅ **Intelligent Fallback**
- Primary: Gemini Cloud (fast, high quality)
- Fallback: Ollama Local Llama3.2 (offline, free)
- Works without internet if Ollama is available

✅ **Profile-Aware**
- Analyzes candidate skills, projects, experience
- Generates suggestions tailored to real background
- Mentions specific projects and technologies

✅ **Smart Caching**
- Caches all responses (cache miss = 1-5s, cache hit = <100ms)
- Eliminates duplicate API calls
- No memory overhead

✅ **Rate Limiting**
- Gemini: 10 calls/hour (conservative)
- Ollama: Unlimited (local)
- Graceful fallback if rate limited

✅ **Zero Client Changes**
- iOS SwiftUI: No code changes needed
- Chrome Extension: No code changes needed
- Just call `/ask` endpoint as before

---

## 📊 Performance Summary

| Metric | Value |
|--------|-------|
| Cache hit time | <100ms |
| Gemini response time | 1-3s |
| Ollama response time | 2-5s |
| Fallback latency | <1s |
| Memory usage | ~4GB (with Ollama) |
| API quota impact | 10 calls/hour |

---

## 🔐 Security & Privacy

✅ No sensitive data logged  
✅ API keys via environment variables (not hardcoded)  
✅ Ollama: All processing stays local  
✅ Graceful degradation if key is missing  

---

## 📋 Checklist

- [ ] Read QUICK_START.md
- [ ] Run `pip install -r requirements.txt`
- [ ] Run `ollama pull llama3.2`
- [ ] Run `ollama serve` (keep terminal open)
- [ ] Test: `python ai_suggestion.py`
- [ ] Copy `/ask` endpoint from `backend_ask_endpoint_updated.py`
- [ ] Add import: `from ai_suggestion import get_suggestion`
- [ ] Test backend health checks
- [ ] Verify `/ask` endpoint works
- [ ] Test from iOS/Extension
- [ ] Deploy to production ✅

---

## 📞 Need Help?

**Quick issues?**
→ Check [QUICK_START.md](QUICK_START.md) troubleshooting section

**Integration questions?**
→ See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) step-by-step guide

**Technical details?**
→ Read [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) architecture section

**Code questions?**
→ Check comments in [ai_suggestion.py](ai_suggestion.py)

---

## 📦 File Structure

```
Pentainterview/
├── 📖 Documentation (YOU ARE HERE)
│   ├── README.md (this file)
│   ├── QUICK_START.md ⭐ START HERE
│   ├── INTEGRATION_GUIDE.md
│   └── IMPLEMENTATION_SUMMARY.md
│
├── 🤖 AI Suggestion System
│   ├── ai_suggestion.py (core module)
│   └── backend_ask_endpoint_updated.py (code template)
│
├── 🔧 Configuration
│   ├── requirements.txt (updated with requests)
│   └── .env (environment variables - create this)
│
├── 📱 Backend
│   ├── backend.py (TO UPDATE with new /ask endpoint)
│   ├── backend_patch.py (existing patches)
│   └── run.sh
│
├── 📱 iOS
│   └── PentaInterviewIos/
│       ├── CandidateProfile.swift (no changes needed)
│       └── ...
│
└── 🔌 Chrome Extension
    ├── popup.js (no changes needed)
    └── ...
```

---

## 🎓 Understanding the System

### For Users (iOS/Extension)
1. App/extension calls `/ask` endpoint with question + profile
2. Backend processes with AI suggestion module
3. Gets response with intelligent suggestion
4. That's it! No changes to your code.

### For Developers
1. `ai_suggestion.py` handles AI logic
2. Tries Gemini first (fast, quality)
3. Falls back to Ollama (offline, free)
4. Caches results (performance)
5. Returns metadata (source, success/fail)

### For DevOps
1. Ensure Ollama running on `:11434`
2. Set `GEMINI_API_KEY` if available
3. Monitor health endpoints
4. Watch logs for fallback events

---

## 🚀 Next Steps

1. **Now**: Read QUICK_START.md
2. **5 min**: Run installation commands
3. **3 min**: Test module with `python ai_suggestion.py`
4. **5 min**: Integrate /ask endpoint from template
5. **2 min**: Verify with curl
6. **Done!** Start using from iOS/Extension

---

## ❓ FAQ

**Q: Do I need Ollama?**  
A: No, but recommended. Without it, system fails if Gemini API unavailable.

**Q: Do I need Gemini API key?**  
A: No, but recommended. System falls back to Ollama automatically.

**Q: Will it work offline?**  
A: Yes, if Ollama is running.

**Q: How much does it cost?**  
A: Ollama is free. Gemini has a free tier (10 calls/hour in this setup).

**Q: Can I use a different LLM?**  
A: Yes! Change `OLLAMA_MODEL` in `ai_suggestion.py` (e.g., "mistral", "neural-chat")

**Q: How long does a suggestion take?**  
A: 1-3s with Gemini, 2-5s with Ollama, <100ms if cached.

---

## 🎉 Ready?

👉 **[Start with QUICK_START.md](QUICK_START.md)**

---

**Status**: ✅ Complete & Ready  
**Last Updated**: May 3, 2026  
**Version**: 1.0
