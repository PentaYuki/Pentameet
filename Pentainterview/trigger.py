import keyboard
import requests
import json

BACKEND_URL = "http://127.0.0.1:5005/ask"

def on_shortcut():
    print("\n[Trigger] Ctrl+Shift+Z pressed! Asking backend...")
    # Gửi câu hỏi mẫu (có thể thay bằng input hoặc transcript)
    payload = {
        "question": "Tell me about your AI experience",
        "profile": {}   # nếu có profile thì thêm vào
    }
    try:
        resp = requests.post(BACKEND_URL, json=payload, timeout=10)
        data = resp.json()
        if resp.ok:
            print(f"→ Suggestion ({data.get('source')}):")
            print(data.get("suggestion", "No content"))
        else:
            print(f"→ Error: {data.get('error', 'Unknown')}")
    except Exception as e:
        print(f"→ Request failed: {e}")

# Đăng ký phím tắt
keyboard.add_hotkey("ctrl+shift+z", on_shortcut)
print("Listening for Ctrl+Shift+Z... (Press ESC to exit)")
keyboard.wait("esc")