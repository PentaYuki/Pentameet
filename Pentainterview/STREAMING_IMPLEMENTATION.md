# Triển khai Streaming SSE cho Gợi ý AI

## 📋 Tóm tắt các thay đổi

Đã triển khai thành công **Server-Sent Events (SSE) streaming** cho gợi ý AI. Bây giờ khi bạn nhấn **Ctrl+Shift+Z**, câu trả lời sẽ xuất hiện từng token một, giống như ChatGPT đang "gõ" câu trả lời.

---

## 🔧 Những gì đã thay đổi

### 1. **Backend (Python/Flask)** – `backend.py`

#### ✅ Thêm imports
```python
from flask import Flask, request, jsonify, Response  # Thêm Response
from ai_suggestion import get_suggestion, _build_system_prompt  # Thêm _build_system_prompt
import requests  # Để gọi Ollama API
```

#### ✅ Endpoint mới: `/ask/stream`
- **Route**: `POST /ask/stream`
- **Body**: `{"question": "...", "profile": {...}, "lang": "en"}`
- **Response**: Server-Sent Events stream (MIME type: `text/event-stream`)
- **Format SSE**: Mỗi dòng là `data: {...}\n\n`
- **Messages**:
  - `{"source": "ollama"}` – nguồn gợi ý
  - `{"token": "..."}` – từng token streaming
  - `{"error": "..."}` – nếu có lỗi
  - `[DONE]` – kết thúc stream

---

### 2. **iOS (Swift)** – `PentaInterviewIos/BackendService.swift`

#### ✅ Class mới: `SSEDecoder`
Parser SSE (Server-Sent Events) chuyên dùng để:
- Nhận dữ liệu từng phần (chunked)
- Parse định dạng SSE (`data: {...}\n\n`)
- Gọi callbacks: `onToken`, `onSource`, `onError`, `onComplete`

```swift
class SSEDecoder: NSObject, URLSessionDataDelegate {
    var onToken: ((String) -> Void)?     // Mỗi token
    var onError: ((String) -> Void)?     // Lỗi
    var onSource: ((String) -> Void)?    // Nguồn
    var onComplete: (() -> Void)?        // Xong
}
```

#### ✅ Method mới: `askForSuggestionStream()`
- Gọi `/ask/stream` endpoint
- Stream tokens vào `suggestion` property
- Tự động xóa transcript khi xong
- Update UI in real-time khi có token mới

---

### 3. **iOS UI** – `PentaInterviewIos/ContentView.swift`

#### ✅ Nút "Gợi ý" thay đổi
```swift
// Trước: Task { await backend.askForSuggestion() }
// Sau:   Task { await backend.askForSuggestionStream() }
```

Nút giờ đây gọi method streaming thay vì regular.

---

## ⚡ Cách hoạt động

### Flow khi nhấn "Gợi ý" (Ctrl+Shift+Z):

```
iPhone → POST /ask/stream → Backend
                           (stream=true)
                              ↓
                          Ollama API
                          (stream=true)
                              ↓
                      Backend: nhận token
                          ↓
                      Gửi qua SSE
                      ("data: {"token": "..."}")
                          ↓
                      iOS: nhận token
                          ↓
                      Update suggestion text
                      (hiển thị ngay)
                          ↓
                      Lặp lại cho token tiếp theo
```

### Timing:

| Phương pháp | Thời gian chờ | Trải nghiệm |
|-----------|----------------|-----------|
| **Regular** | Chờ ~3-5s rồi thấy toàn bộ | Cảm giác "máy tính đang suy nghĩ" |
| **Streaming** | Thấy token ngay từ đầu | Cảm giác "AI đang gõ câu trả lời" |

---

## 🧪 Cách test

### 1. **Start Ollama**
```bash
ollama serve
```

### 2. **Start Backend**
```bash
cd /Users/gooleseswsq1gmail.com/Documents/Pentainterview
python3 backend.py
```

### 3. **Test streaming endpoint** (Terminal khác)
```bash
python3 test_streaming.py
```

Hoặc dùng curl:
```bash
curl -N -X POST http://localhost:5005/ask/stream \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Tell me about your experience",
    "profile": {"name": "Test", "skills": {"languages": ["Python"]}},
    "lang": "en"
  }'
```

Bạn sẽ thấy từng token xuất hiện liên tục:
```
data: {"source":"ollama"}

data: {"token":"I"}

data: {"token":" have"}

data: {"token":" 3"}

...

data: [DONE]
```

### 4. **Test iOS app**
- Build iOS app
- Connect to backend
- Nói một câu hỏi
- Nhấn **Gợi ý** (Ctrl+Shift+Z) hoặc nút "Gợi ý"
- Xem gợi ý xuất hiện từng chữ một!

---

## 📝 Lưu ý quan trọng

### ✅ Hỗ trợ
- **Ollama**: ✅ Fully supported (stream từ Ollama API)
- **Gemini Cloud**: ⏳ Không stream trực tiếp (phức tạp, cần Gemini SDK v2)
- **Tiếng Anh**: ✅ Streaming toàn bộ
- **Tiếng Việt**: ⏳ Sau stream xong, có thể gọi `/ask` để dịch (2 request)

### ⚙️ Configuration
- **Streaming đã bật** cho Ollama
- **Temperature**: 0.35 (ổn định, không quá sáng tạo)
- **Token limit**: 150 (đủ cho gợi ý)
- **Timeout**: 60 giây (cho streaming dài)

### 🔒 Performance
- **Bandwidth**: Minimal (chỉ stream token, không file lớn)
- **CPU**: Tương tự /ask, nhưng UI mượt hơn
- **UX**: Tốt hơn vì user thấy ngay kết quả

---

## 🎯 Các tính năng có thể mở rộng sau

1. **Gemini streaming**: Dùng Gemini SDK v2 `stream_config`
2. **Translate streaming**: Stream tiếng Việt trực tiếp (phức tạp)
3. **Streaming cho /summarize**: Tóm tắt câu dài in real-time
4. **Caching streaming**: Lưu suggestion đã stream (tối ưu hóa)
5. **WebSocket alternative**: Thay SSE bằng WebSocket nếu cần bidirectional

---

## 📚 File được sửa đổi

| File | Thay đổi |
|------|---------|
| `backend.py` | +3 imports, +1 endpoint `/ask/stream` (~100 dòng) |
| `BackendService.swift` | +1 class `SSEDecoder` (+60 dòng), +1 method `askForSuggestionStream()` (+55 dòng) |
| `ContentView.swift` | Nút "Gợi ý" thay đổi method (1 dòng) |

---

## ✨ Kết quả

Khi triển khai thành công:
- ✅ Nút "Gợi ý" sử dụng streaming
- ✅ Transcript tự xóa sau khi có gợi ý
- ✅ Thấy gợi ý từng chữ một xuất hiện
- ✅ UI không bị "freeze" khi chờ
- ✅ Lỗi được hiển thị ngay

---

## 🐛 Troubleshooting

| Vấn đề | Nguyên nhân | Giải pháp |
|--------|-----------|----------|
| "Ollama not running" | Ollama chưa start | `ollama serve` |
| Empty suggestion | Model không có response | Check Ollama logs |
| UI lag | Backend bị overload | Giảm `num_predict` từ 150 → 100 |
| Streaming bị cắt | Network timeout | Tăng `timeoutInterval` từ 60 → 120 |

---

## 🚀 Ready?

1. ✅ Backend có `/ask/stream` endpoint
2. ✅ iOS có `SSEDecoder` + `askForSuggestionStream()`
3. ✅ Nút UI đã cập nhật

**Bây giờ:**
1. Build iOS app mới
2. Start backend + Ollama
3. Test streaming
4. Enjoy! 🎉

Hỏi nếu cần help!
