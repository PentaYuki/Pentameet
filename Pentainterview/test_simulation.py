import os
import google.generativeai as genai

# Setup Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    print("[ERROR] GEMINI_API_KEY not found.")
else:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-flash-latest")

    # Technical question simulation
    question = "Can you explain the difference between a microservices architecture and a monolithic one, specifically regarding scalability and fault tolerance in a Kubernetes environment?"
    
    print(f"Simulating Question: {question}")
    
    prompt = (
        "You are a concise interview coach. The interviewer just asked a question.\n"
        "Reply ONLY with the suggested answer — no intro, no labels.\n"
        "Max 40 words. Use 2–3 short bullet points starting with '•'.\n"
        "Be confident, specific, and professional.\n\n"
        f"Question: {question}\n"
        "Suggested answer:"
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=120,
                temperature=0.4,
            ),
        )
        print("\n--- Gemini 1.5 Flash 8b Response ---")
        print(response.text.strip())
        print("------------------------------------\n")
    except Exception as e:
        print(f"[Error] Gemini call failed: {e}")

# Faster-Whisper Base Test (Local)
from faster_whisper import WhisperModel
import numpy as np

print("Testing Faster-Whisper 'base' model loading...")
try:
    whisper_model = WhisperModel("base", device="cpu", compute_type="float32")
    print("✓ Faster-Whisper 'base' model loaded successfully.")
    
    # Simulate a tiny audio chunk (silence) to verify transcribe call works
    dummy_audio = np.zeros(16000, dtype=np.float32)
    segments, info = whisper_model.transcribe(dummy_audio, beam_size=1)
    print("✓ Transcription call successful.")
except Exception as e:
    print(f"✗ Faster-Whisper test failed: {e}")
