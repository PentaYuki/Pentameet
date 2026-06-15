# 🚀 Penta Suite: PentaMeet & PentaInterview

Chào mừng bạn đến với **Penta Suite** – bộ công cụ hỗ trợ giao tiếp và phỏng vấn thời gian thực được hỗ trợ bởi các công nghệ AI tiên tiến (Apple Translation Framework, Speech-to-Text, Gemini API Cloud & Ollama Local).

Repository này bao gồm 2 dự án chính:
1. **PentaMeet**: Ứng dụng macOS native (SwiftUI) giúp nhận dạng giọng nói, dịch thuật trực tiếp bằng framework của Apple và đọc kết quả (TTS).
2. **PentaInterview**: Hệ thống hỗ trợ phỏng vấn real-time bao gồm Chrome Extension, Python Backend (VAD + Whisper + Gemini/Ollama) và ứng dụng iOS client.

---

## 📂 Cấu trúc Repository

```text
Pentameet/ (Root)
├── README.md                      # File hướng dẫn này
├── .gitignore                     # Cấu hình bỏ qua các file rác khi Git commit
├── Pentameet/                     # [Dự án 1] Ứng dụng macOS SwiftUI (PentaMeet)
│   ├── Pentameet.xcodeproj        # Xcode Project
│   └── Pentameet/                 # Mã nguồn Swift (Speech Engine, Translation Service, TTS...)
└── Pentainterview/                # [Dự án 2] Hệ thống trợ lý phỏng vấn (PentaInterview)
    ├── manifest.json              # Manifest của Chrome Extension
    ├── background.js / popup.*    # Mã nguồn giao diện & logic Chrome Extension
    ├── backend.py                 # Backend Python xử lý Audio, VAD, Whisper & Gemini
    ├── ai_suggestion.py           # Engine AI tạo gợi ý phỏng vấn (Gemini Cloud ↔ Ollama Local)
    └── PentaInterviewIos/         # Dự án ứng dụng khách iOS
```

---

## 🎤 1. PentaMeet (macOS App)

Ứng dụng macOS native được thiết kế để hỗ trợ dịch thuật trực tiếp các buổi họp (Google Meet, Zoom...) ngay trên máy tính của bạn.

### ✨ Tính năng chính
* **Nhận dạng giọng nói (STT):** Sử dụng `SFSpeechRecognizer` nội bộ của Apple với độ trễ cực thấp.
* **Dịch thuật on-device:** Tích hợp framework `Translation` chính chủ của Apple (mới từ macOS Sequoia / iOS 18), chạy trực tiếp trên máy không cần API Key và hoàn toàn miễn phí.
* **Text-To-Speech (TTS):** Đọc bản dịch tự động bằng `AVSpeechSynthesizer` với khả năng tùy chỉnh tốc độ, cao độ.
* **Hỗ trợ Loopback/BlackHole:** Hỗ trợ lấy âm thanh hệ thống (âm thanh cuộc gọi từ trình duyệt hoặc app họp) thông qua driver âm thanh ảo.
* **Giao diện Glassmorphism hiện đại:** Thiết kế 2 bảng song song (Gốc & Dịch) trực quan, tự động cuộn (Auto-Scroll), hỗ trợ copy nhanh.

### ⚙️ Cài đặt & Chạy ứng dụng
1. Yêu cầu hệ điều hành: **macOS 15 (Sequoia)** trở lên để hỗ trợ framework `Translation`.
2. Mở file [Pentameet.xcodeproj](file:///Users/gooleseswsq1gmail.com/Documents/PentaMeet/Pentameet/Pentameet.xcodeproj) bằng **Xcode**.
3. Cài đặt Driver âm thanh ảo (Khuyên dùng **BlackHole**):
   ```bash
   brew install --cask blackhole-2ch
   ```
4. Chọn thiết bị đầu vào trong PentaMeet là **BlackHole 2ch** để bắt đầu thu âm thanh từ hệ thống (hoặc dùng Microphone mặc định của Mac).
5. Nhấn **Run (⌘R)** trên Xcode để khởi chạy ứng dụng.

---

## 🎙️ 2. PentaInterview (Chrome Extension & iOS App)

Hệ thống hỗ trợ trả lời phỏng vấn real-time tự động: **Silero VAD thông minh → STT Whisper cục bộ → Sinh gợi ý trả lời qua Gemini Flash Cloud (với fallback sang Ollama Local)**.

### ✨ Tính năng chính
* **VAD (Voice Activity Detection):** Sử dụng Silero VAD để lọc tiếng ồn và phát hiện chính xác khi nào người phỏng vấn bắt đầu/dừng nói.
* **Whisper STT Local:** Tự động chuyển giọng nói thành văn bản bằng Whisper model (chạy local trên máy).
* **Smart AI Suggestions:** Tự động sinh câu trả lời gợi ý bằng tiếng Anh khớp với **Profile ứng viên** (kỹ năng, dự án, kinh nghiệm).
* **Cơ chế Fallback thông minh:**
  * **Primary (Cloud):** Sử dụng Gemini 1.5 Flash (nhanh, chất lượng cao).
  * **Secondary (Local/Offline):** Tự động chuyển hướng sang Ollama Local (chạy Llama 3.2 offline) khi mất mạng hoặc hết quota API Gemini.
* **Chrome Extension Client:** Hiển thị trực tiếp phụ đề và gợi ý trả lời ngay trên trình duyệt khi họp Google Meet.
* **iOS Companion App:** Ứng dụng iOS đi kèm giúp xem transcript và gợi ý câu trả lời từ thiết bị di động.

### ⚙️ Cài đặt & Sử dụng

#### Bước 1: Cài đặt Dependencies & Backend Python
1. Truy cập thư mục [Pentainterview](file:///Users/gooleseswsq1gmail.com/Documents/PentaMeet/Pentameet/Pentainterview):
   ```bash
   cd Pentainterview
   ```
2. Cài đặt thư viện Python:
   ```bash
   pip install -r requirements.txt
   ```
3. Cấu hình API Key cho Gemini (Tạo file `.env` hoặc export biến môi trường):
   ```bash
   export GEMINI_API_KEY="api_key_cua_ban"
   ```
4. Chạy Backend server:
   ```bash
   python backend.py
   ```

#### Bước 2: Khởi động Local LLM (Ollama) làm Fallback (Tùy chọn)
1. Tải và cài đặt [Ollama](https://ollama.com).
2. Tải model Llama 3.2:
   ```bash
   ollama pull llama3.2
   ```
3. Khởi chạy Ollama:
   ```bash
   ollama serve
   ```

#### Bước 3: Cài đặt Chrome Extension
1. Mở trình duyệt Chrome và truy cập đường dẫn `chrome://extensions/`.
2. Bật chế độ **Developer mode** ở góc trên bên phải.
3. Click nút **Load unpacked** và chọn thư mục [Pentainterview](file:///Users/gooleseswsq1gmail.com/Documents/PentaMeet/Pentameet/Pentainterview) (nơi chứa file `manifest.json`).
4. Ghim extension lên thanh công cụ để sử dụng tiện lợi.

#### Bước 4: Ứng dụng iOS client
Mã nguồn nằm tại thư mục [PentaInterviewIos](file:///Users/gooleseswsq1gmail.com/Documents/PentaMeet/Pentameet/Pentainterview/PentaInterviewIos), bạn có thể build và chạy trên iPhone bằng Xcode để theo dõi gợi ý phỏng vấn từ màn hình điện thoại.

---

## 🤝 Hướng dẫn Phối Hợp & Ghi Chú Phát Triển

* **Bảo mật:** Không bao giờ commit các file `.env`, `gitconfig` hay file cấu hình chứa API Key của bạn lên GitHub.
* **Định dạng file:** Khi chỉnh sửa code Swift hoặc Python, hãy đảm bảo định dạng thụt lề chuẩn (Xcode: Tabs/Spaces, Python: 4 Spaces) để tránh lỗi cú pháp.
* **Đóng góp:** Vui lòng tạo branch mới cho từng tính năng và tạo Pull Request thay vì push trực tiếp lên nhánh `main` khi làm việc nhóm lớn.

Chúc bạn có những trải nghiệm phỏng vấn và dịch thuật tuyệt vời cùng **Penta Suite**! 🚀
