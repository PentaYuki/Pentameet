"""
ai_suggestion.py
================
Module gợi ý câu trả lời với fallback: Gemini Cloud → Llama3.2 Local

Khoa's Interview Assistant - Lưu ý sử dụng:
1. Cài đặt ollama: https://ollama.ai
2. Pull model: ollama pull llama3.2
3. Chạy: ollama serve (mặc định port 11434)
"""

import os
import json
import requests
from typing import Optional
import google.genai as genai
from google.genai import types
from datetime import datetime, timedelta

# ─── Config ────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = "llama3.2"  # hoặc "mistral", "neural-chat", etc.

# Cache gợi ý để tránh duplicate API calls
_suggestion_cache = {}
_api_call_times = []
MAX_API_CALLS_PER_HOUR = 10

# ────────────────────────────────────────────────────────────────────────

def _is_rate_limited() -> bool:
    """Kiểm tra xem đã vượt quá rate limit chưa."""
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    global _api_call_times
    _api_call_times = [t for t in _api_call_times if t > one_hour_ago]
    return len(_api_call_times) >= MAX_API_CALLS_PER_HOUR


def _record_api_call():
    """Ghi lại một API call để track rate limit."""
    global _api_call_times
    _api_call_times.append(datetime.now())


def _build_system_prompt(profile: dict) -> str:
    """
    Xây dựng system prompt dựa trên CandidateProfile.
    Tổng hợp thông tin để AI có context tốt.
    """
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
            f"Japanese Level: {profile.get('japanese_level', '')}\n"
            f"=========================\n"
        )

    system_prompt = (
        "You are an expert interview coach helping a candidate answer live interview questions.\n"
        "Reply ONLY with the suggested answer — no intro, no labels, no markdown headers.\n"
        "Use 2–3 short bullet points starting with '•'.\n"
        "Max 50 words total. Be confident, specific, and tailor the answer to the candidate's real experience.\n"
        "IMPORTANT: The candidate works ALONE, not in a team. Avoid any mention of teammates, collaborators, or group work.\n"
        "Always use first-person singular (I, my).\n"
        "Reference specific projects or skills from the profile when relevant.\n"
        f"{profile_block}\n"
    )
    return system_prompt


# ────────────────────────────────────────────────────────────────────────
# PRIMARY: Gemini Cloud
# ────────────────────────────────────────────────────────────────────────

def _get_suggestion_gemini(question: str, profile: dict) -> Optional[str]:
    """
    Gợi ý từ Gemini Cloud.
    Trả về None nếu: API key không có, rate limited, hoặc API error.
    """
    if not GEMINI_API_KEY:
        print("[Gemini] API key not set, skipping...")
        return None

    if _is_rate_limited():
        print("[Gemini] Rate limited, falling back to Ollama...")
        return None

    try:
        gemini_model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            api_key=GEMINI_API_KEY
        )

        system_prompt = _build_system_prompt(profile)
        full_prompt = f"{system_prompt}\nInterviewer's question: {question}\nSuggested answer (English, bullet points):"

        response = gemini_model.generate_content(
            full_prompt,
            generation_config=types.GenerationConfig(
                max_output_tokens=150,
                temperature=0.35,
            ),
        )

        suggestion = response.text.strip()
        _record_api_call()
        print(f"[Gemini] ✓ Generated suggestion ({len(suggestion)} chars)")
        return suggestion

    except Exception as e:
        print(f"[Gemini] Error: {e} - Falling back to Ollama...")
        return None


# ────────────────────────────────────────────────────────────────────────
# FALLBACK: Ollama Local (Llama3.2)
# ────────────────────────────────────────────────────────────────────────

def _get_suggestion_ollama(question: str, profile: dict) -> Optional[str]:
    """
    Gợi ý từ Ollama Local (Llama3.2).
    Trả về None nếu Ollama không available.

    Yêu cầu:
      ollama pull llama3.2
      ollama serve (chạy ở port 11434)
    """
    try:
        system_prompt = _build_system_prompt(profile)
        full_prompt = f"{system_prompt}\nInterviewer's question: {question}\nSuggested answer (English, bullet points):"

        # Gọi Ollama generate endpoint
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.35,
                    "num_predict": 150,
                }
            },
            timeout=30,
        )

        if response.status_code != 200:
            print(f"[Ollama] HTTP {response.status_code}: {response.text[:100]}")
            return None

        data = response.json()
        suggestion = data.get("response", "").strip()

        if suggestion:
            print(f"[Ollama] ✓ Generated suggestion ({len(suggestion)} chars) [LOCAL]")
            return suggestion

        return None

    except requests.exceptions.ConnectionError:
        print(f"[Ollama] ✗ Connection failed - Server not running?")
        print(f"         Start with: ollama serve")
        return None
    except Exception as e:
        print(f"[Ollama] Error: {e}")
        return None


# ────────────────────────────────────────────────────────────────────────
# PUBLIC: Wrapper với fallback logic
# ────────────────────────────────────────────────────────────────────────

def get_suggestion(question: str, profile: dict = None, lang: str = "en") -> dict:
    """
    Lấy gợi ý câu trả lời với fallback strategy:
    1. Gemini Cloud (nếu API key + không rate limited)
    2. Ollama Local Llama3.2 (fallback)
    3. Return error message nếu cả hai thất bại

    Args:
        question: Câu hỏi phỏng vấn (string)
        profile: CandidateProfile dict (optional)

    Returns:
        {
            "success": bool,
            "suggestion": str (hoặc error message),
            "source": "gemini" | "ollama" | "error",
        }
    """
    profile = profile or {}

    # Cache key
    cache_key = f"{question}|{json.dumps(profile, sort_keys=True, default=str)}"
    if cache_key in _suggestion_cache:
        print("[Cache] ✓ Hit!")
        return {
            "success": True,
            "suggestion": _suggestion_cache[cache_key],
            "source": "cache",
        }

    # Try Gemini first
    print("\n[Ask] Trying Gemini Cloud...")
    suggestion = _get_suggestion_gemini(question, profile)
    if suggestion:
        _suggestion_cache[cache_key] = suggestion
        return {
            "success": True,
            "suggestion": suggestion,
            "source": "gemini",
        }

    # Fallback to Ollama Local
    print("[Ask] Falling back to Ollama Local (Llama3.2)...")
    suggestion = _get_suggestion_ollama(question, profile)
    if suggestion:
        _suggestion_cache[cache_key] = suggestion
        return {
            "success": True,
            "suggestion": suggestion,
            "source": "ollama",
        }

    # Both failed
    error_msg = (
        "❌ Could not generate suggestion.\n"
        "Make sure:\n"
        "  • Gemini API key is set (export GEMINI_API_KEY=...)\n"
        "  • OR Ollama is running (ollama serve) with llama3.2 model\n"
        "  • OR install: ollama pull llama3.2"
    )
    # Trước return thành công, thêm đoạn:
    if lang != "en":
        translation = translate_suggestion(suggestion, lang)
        if translation:
            suggestion = translation
        else:
            # Fallback: trả về gốc + cảnh báo
            suggestion = f"(Translation failed)\n{suggestion}"
    return {
        "success": False,
        "suggestion": error_msg,
        "source": "error",
    }

def translate_suggestion(suggestion: str, target_lang: str = "vi") -> Optional[str]:
    """
    Dịch gợi ý từ tiếng Anh sang ngôn ngữ khác (mặc định tiếng Việt).
    Dùng Ollama local (không tốn API Gemini).
    """
    prompt = (
        f"Translate the following English text into {target_lang}.\n"
        "Keep the bullet points and structure. Just return the translation, no extra text.\n\n"
        f"English:\n{suggestion}\n\nTranslation:"
    )
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 300}
            },
            timeout=30
        )
        if resp.status_code == 200:
            translated = resp.json().get("response", "").strip()
            if translated:
                return translated
    except Exception as e:
        print(f"[Translate] Error: {e}")
    return None
# ────────────────────────────────────────────────────────────────────────
# Test function
# ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test profile
    test_profile = {
        "name": "Lê Đăng Khoa",
        "target_roles": ["AI Full Stack Engineer", "Bridge Software Engineer"],
        "skills": {
            "languages": ["Python", "Swift", "JavaScript"],
            "frameworks": ["FastAPI", "SwiftUI", "React"],
            "ai_tools": ["Gemini API", "Ollama", "LangChain"],
            "infra": ["Docker", "PostgreSQL", "Vercel"],
        },
        "projects": [
            {"name": "PentaSchool (LMS)", "desc": "Full learning management system with AI auto-grading"},
            {"name": "PentaMO (AI Marketplace)", "desc": "AI-powered motorcycle marketplace"},
        ],
        "experience": "Self-taught developer, JLPT N3",
        "japanese_level": "JLPT N3 (studying N2)",
        "background": "Transitioned from manufacturing to software, specializes in local-first AI systems",
    }

    # Test questions
    test_questions = [
        "Tell me about your AI experience",
        "What's your strongest project?",
        "How do you handle real-time systems?"
    ]

    print("=" * 70)
    print("AI SUGGESTION MODULE TEST")
    print("=" * 70)

    for q in test_questions:
        print(f"\n📌 Question: {q}")
        result = get_suggestion(q, test_profile)
        print(f"   Source: {result['source']}")
        print(f"   Suggestion:\n   {result['suggestion']}")
        print()
