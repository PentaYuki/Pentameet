# 🎙 Interview Assistant v2

Hệ thống hỗ trợ phỏng vấn real-time: **VAD thông minh → STT cục bộ → Gemini Flash trên Cloud**.

```
[Google Meet] ──► [BlackHole] ──► [Python Backend]
                                       │
                              ┌────────┼────────────┐
                              │        │             │
                           Silero   Whisper      Gemini
                             VAD    tiny.en    1.5 Flash
                              │        │             │
                              └────────┴──────┬──────┘
                                              │
                                     [Chrome Extension]
                                     (Popup hiển thị)
```

---

## ⚡ Cài đặt nhanh

### 1. Cài BlackHole (một lần duy nhất)
```bash
brew install --cask blackhole-2ch
```
Sau khi cài: **System Settings → Sound → Output** → chọn **BlackHole 2ch**.

> ⚠️ **LUÔN dùng tai nghe khi phỏng vấn** để tránh echo/loopback.

### 2. Backend Python
```bash
cd backend/
pip install -r requirements.txt

export GEMINI_API_KEY="your_key_here"
python backend.py
```

Lần đầu chạy sẽ tải Silero VAD model (~5MB) và Whisper tiny.en (~75MB).

### 3. Chrome Extension
1. Mở Chrome → `chrome://extensions/`
2. Bật **Developer mode** (góc trên phải)
3. Click **Load unpacked** → chọn thư mục `extension/`
4. Ghim extension vào toolbar

---

## 🎮 Cách dùng trong phỏng vấn

| Hành động | Cách thực hiện |
|-----------|---------------|
| Xem transcript người phỏng vấn | Tự động hiện trong popup |
| Lấy gợi ý trả lời | `⌘⇧A` hoặc nút **Lấy gợi ý** |
| Xoá và bắt đầu câu mới | `⌘⇧C` hoặc icon thùng rác |
| Reconnect backend | Click vào pill **Offline** |

### Trạng thái màu sắc
- 🟠 **Cam nhấp nháy** → Interviewer đang nói
- 🔵 **Xanh dương** → Đang nhận dạng giọng nói
- ⚫ **Tối** → Chờ
- 🔴 **Đỏ** → Mất kết nối

---

## ⚙️ Tinh chỉnh

Mở `backend/backend.py` và điều chỉnh các biến đầu tệp:

```python
VAD_THRESHOLD = 0.50   # Tăng nếu bắt nhầm tiếng ồn (0.4 – 0.7)
SILENCE_LIMIT = 1.0    # Giây chờ im lặng để kết thúc câu (0.8 – 1.2)
BLACKHOLE_NAME = "BlackHole 2ch"  # Đổi nếu tên thiết bị khác
```

---

## 🐛 Troubleshooting

**"Không tìm thấy BlackHole"**
→ Chạy `python -c "import sounddevice; print(sounddevice.query_devices())"` để xem danh sách thiết bị.

**Popup hiện "Offline"**
→ Đảm bảo `python backend.py` đang chạy. Click icon reconnect trong popup.

**Transcript bị cắt cụt**
→ Tăng `SILENCE_LIMIT` lên `1.2` hoặc `1.5`.

**Transcript bắt nhầm tiếng ồn**
→ Tăng `VAD_THRESHOLD` lên `0.6`.

**Gemini trả lời chậm**
→ Kiểm tra kết nối internet. Thử đổi model sang `gemini-1.5-flash-8b` (nhẹ hơn).
