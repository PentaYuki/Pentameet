// BackendService.swift
// Interview Assistant iOS
// Kết nối với Mac backend qua HTTP polling + REST

import Foundation
import Combine

// MARK: - SSEDecoder (Server-Sent Events Parser)

class SSEDecoder: NSObject, URLSessionDataDelegate {
    private var buffer = ""
    var onToken: ((String) -> Void)?
    var onError: ((String) -> Void)?
    var onSource: ((String) -> Void)?
    var onComplete: (() -> Void)?

    // Nhận dữ liệu tăng dần từ server
    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive data: Data) {
        guard let chunk = String(data: data, encoding: .utf8) else { return }
        buffer += chunk
        processBuffer()
    }

    // Xử lý khi kết thúc hoặc lỗi
    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        if let error = error {
            onError?(error.localizedDescription)
        }
    }

    private func processBuffer() {
        // Tách dòng bằng \n\n (định dạng SSE)
        while let range = buffer.range(of: "\n\n") {
            let line = String(buffer[..<range.lowerBound])
            buffer = String(buffer[range.upperBound...])
            parseSSELine(line)
        }
    }

    private func parseSSELine(_ line: String) {
        // Mỗi dòng SSE bắt đầu bằng "data: "
        if line.hasPrefix("data: ") {
            let jsonString = String(line.dropFirst(6))
            if jsonString == "[DONE]" {
                onComplete?()
            } else {
                guard let data = jsonString.data(using: .utf8) else { return }
                do {
                    let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any]
                    if let source = obj?["source"] as? String {
                        onSource?(source)
                    } else if let token = obj?["token"] as? String {
                        onToken?(token)
                    } else if let error = obj?["error"] as? String {
                        onError?(error)
                    }
                } catch {
                    // Ignore malformed JSON
                }
            }
        }
    }
}

// MARK: - Models

struct PollResponse: Decodable {
    let events: [BackendEvent]
    let transcriptEn: String
    let transcriptVi: String
    let status: String
    let ts: Double

    enum CodingKeys: String, CodingKey {
        case events
        case transcriptEn = "transcript_en"
        case transcriptVi = "transcript_vi"
        case status, ts
    }
}

struct BackendEvent: Decodable {
    let type: String
    let data: BackendEventData
    let ts: Double
}

struct BackendEventData: Decodable {
    let state: String?
    let text: String?
    let textVi: String?
    let fullEn: String?
    let fullVi: String?

    enum CodingKeys: String, CodingKey {
        case state, text
        case textVi  = "text_vi"
        case fullEn  = "full_en"
        case fullVi  = "full_vi"
    }
}

struct AskResponse: Decodable {
    let success: Bool?
    let suggestion: String?
    let error: String?
    let source: String?  // "gemini", "ollama", "cache", "error"
    let processingTime: Double?

    enum CodingKeys: String, CodingKey {
        case success, suggestion, error, source
        case processingTime = "processing_time"
    }
}

struct SummarizeResponse: Decodable {
    let summaryVi: String?
    let error: String?
    enum CodingKeys: String, CodingKey {
        case summaryVi = "summary_vi"
        case error
    }
}

// MARK: - BackendService

@MainActor
class BackendService: ObservableObject {

    // ── Published state ──────────────────────────────────────────────
    @Published var isConnected     = false
    @Published var status          = "idle"       // idle | speaking | transcribing | disconnected
    @Published var transcriptEn    = ""
    @Published var transcriptVi    = ""
    @Published var suggestion      = ""
    @Published var suggestionSource = ""         // "gemini", "ollama", "cache", "error"
    @Published var summaryVi       = ""           // Tóm tắt câu dài → tiếng Việt
    @Published var isLoadingSuggest = false
    @Published var isLoadingSummary = false
    @Published var errorMessage    = ""

    // ── Config ───────────────────────────────────────────────────────
    @Published var backendHost: String {
        didSet { UserDefaults.standard.set(backendHost, forKey: "backendHost") }
    }

    var baseURL: String { "http://\(backendHost):5005" }

    // Auto-summarize khi transcript dài hơn ngưỡng này (words)
    let summarizeThreshold = 30

    // ── Internal ─────────────────────────────────────────────────────
    private var pollTimer: Timer?
    private var lastPollTs: Double = 0
    private var pollErrorCount = 0
    private let session: URLSession

    init() {
        // Mặc định dùng localhost (cho simulator), nếu dùng iPhone thật hãy đổi thành IP của Mac
        let saved = UserDefaults.standard.string(forKey: "backendHost") ?? "127.0.0.1"
        self.backendHost = saved

        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 5
        config.timeoutIntervalForResource = 10
        self.session = URLSession(configuration: config)
    }

    // MARK: – Connection lifecycle

    func startPolling() {
        stopPolling()
        pollTimer = Timer.scheduledTimer(withTimeInterval: 1.2, repeats: true) { [weak self] _ in
            Task { await self?.poll() }
        }
        // First check immediately
        Task { await self.healthCheck() }
    }

    func stopPolling() {
        pollTimer?.invalidate()
        pollTimer = nil
    }

    private func healthCheck() async {
        guard let url = URL(string: "\(baseURL)/health") else { return }
        do {
            let (_, response) = try await session.data(from: url)
            let ok = (response as? HTTPURLResponse)?.statusCode == 200
            isConnected = ok
            if ok { pollErrorCount = 0; status = "idle" }
        } catch {
            isConnected = false
            status = "disconnected"
        }
    }

    // MARK: – Polling

    private func poll() async {
        guard let url = URL(string: "\(baseURL)/poll?since=\(lastPollTs)") else { return }
        do {
            let (data, response) = try await session.data(from: url)
            guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw URLError(.badServerResponse) }

            let decoded = try JSONDecoder().decode(PollResponse.self, from: data)
            applyPollResponse(decoded)
            pollErrorCount = 0

            if !isConnected {
                isConnected = true
                errorMessage = ""
            }
        } catch {
            pollErrorCount += 1
            if pollErrorCount >= 3 {
                isConnected = false
                status = "disconnected"
            }
        }
    }

    private func applyPollResponse(_ r: PollResponse) {
        // Update timestamp for next poll
        lastPollTs = r.ts

        // Apply events in order
        for event in r.events {
            switch event.type {
            case "status":
                if let s = event.data.state { status = s }
            case "transcript":
                // Use full accumulated values from backend
                transcriptEn = r.transcriptEn
                transcriptVi = r.transcriptVi

                // Auto-summarize if long enough
                let wordCount = r.transcriptEn.split(separator: " ").count
                if wordCount >= summarizeThreshold && summaryVi.isEmpty {
                    Task { await self.requestSummary(text: r.transcriptEn) }
                }
            case "clear":
                transcriptEn = ""
                transcriptVi = ""
                summaryVi    = ""
                suggestion   = ""
                status       = "idle"
            default: break
            }
        }

        // Sync full state (handles cases where events were missed)
        if transcriptEn != r.transcriptEn { transcriptEn = r.transcriptEn }
        if transcriptVi != r.transcriptVi { transcriptVi = r.transcriptVi }
        if status != r.status && !r.status.isEmpty { status = r.status }
    }

    // MARK: – Summarize (câu hỏi dài → tóm tắt tiếng Việt)

    func requestSummary(text: String) async {
        guard !text.isEmpty, !isLoadingSummary else { return }
        guard let url = URL(string: "\(baseURL)/summarize") else { return }

        isLoadingSummary = true
        defer { isLoadingSummary = false }

        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONSerialization.data(withJSONObject: ["text": text])

        do {
            let (data, _) = try await session.data(for: req)
            let decoded = try JSONDecoder().decode(SummarizeResponse.self, from: data)
            if let s = decoded.summaryVi, !s.isEmpty {
                summaryVi = s
            }
        } catch {
            print("[Summarize] Error: \(error)")
        }
    }

    // MARK: – Ask Gemini (gợi ý trả lời tiếng Anh)

    func askForSuggestion() async {
        let question = transcriptEn.trimmingCharacters(in: .whitespaces)
        guard !question.isEmpty, !isLoadingSuggest else { return }
        guard let url = URL(string: "\(baseURL)/ask") else { return }

        isLoadingSuggest = true
        suggestion = ""
        errorMessage = ""
        defer { isLoadingSuggest = false }

        let body: [String: Any] = [
            "question": question,
            "profile":  CandidateProfile.current.asDict,
            "lang": "vi"      // hoặc để "en" nếu muốn tiếng Anh
        ]

        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = 30
        req.httpBody = try? JSONSerialization.data(withJSONObject: body)

        do {
            let (data, response) = try await session.data(for: req)
            let httpResponse = response as? HTTPURLResponse
            let statusCode = httpResponse?.statusCode ?? 0
            
            let decoded = try JSONDecoder().decode(AskResponse.self, from: data)
            
            // Handle success case
            if let s = decoded.suggestion, !(s.isEmpty) {
                suggestion = s
                suggestionSource = decoded.source ?? "unknown"
                
                // Log source for debugging
                let sourceLabel = sourceLabel(decoded.source ?? "error")
                print("[Ask] ✓ Got suggestion from \(sourceLabel) in \(decoded.processingTime ?? 0)s")
                
                // Clear transcript after getting suggestion
                await clearTranscript()
            } else if let e = decoded.error, !(e.isEmpty) {
                errorMessage = e
                suggestionSource = "error"
                print("[Ask] ✗ Error: \(e)")
            } else {
                errorMessage = "No suggestion returned"
                suggestionSource = "error"
            }
        } catch {
            errorMessage = "Lỗi kết nối: \(error.localizedDescription)"
            suggestionSource = "error"
        }
    }

    // MARK: – Ask Streaming (gợi ý theo stream SSE)

    func askForSuggestionStream() async {
        let question = transcriptEn.trimmingCharacters(in: .whitespaces)
        guard !question.isEmpty, !isLoadingSuggest else { return }

        isLoadingSuggest = true
        suggestion = ""          // xóa gợi ý cũ
        errorMessage = ""

        let body: [String: Any] = [
            "question": question,
            "profile": CandidateProfile.current.asDict,
            "lang": "en"        // stream hiện tại chỉ hỗ trợ tiếng Anh
        ]

        var req = URLRequest(url: URL(string: "\(baseURL)/ask/stream")!)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = 60
        req.httpBody = try? JSONSerialization.data(withJSONObject: body)

        let decoder = SSEDecoder()
        decoder.onSource = { [weak self] source in
            DispatchQueue.main.async {
                self?.suggestionSource = source
                print("[Stream] Source: \(source)")
            }
        }
        decoder.onToken = { [weak self] token in
            DispatchQueue.main.async {
                self?.suggestion += token
            }
        }
        decoder.onError = { [weak self] error in
            DispatchQueue.main.async {
                self?.errorMessage = error
                self?.isLoadingSuggest = false
                print("[Stream] Error: \(error)")
            }
        }
        decoder.onComplete = { [weak self] in
            DispatchQueue.main.async {
                self?.isLoadingSuggest = false
                print("[Stream] ✓ Streaming completed")
                // Xóa transcript sau khi hoàn tất
                Task { await self?.clearTranscript() }
            }
        }

        let session = URLSession(configuration: .default, delegate: decoder, delegateQueue: nil)
        let task = session.dataTask(with: req)
        task.resume()
    }

    // MARK: – Clear

    func clearTranscript() async {
        transcriptEn = ""
        transcriptVi = ""
        summaryVi    = ""
        suggestion   = ""
        errorMessage = ""
        lastPollTs   = 0

        guard let url = URL(string: "\(baseURL)/poll/clear") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        _ = try? await session.data(for: req)
    }

    // MARK: – Helpers

    private func sourceLabel(_ source: String) -> String {
        switch source {
        case "gemini": return "☁️ Gemini (Cloud)"
        case "ollama": return "💻 Ollama (Local)"
        case "cache": return "⚡ Cache"
        case "error": return "❌ Error"
        default: return "❓ Unknown"
        }
    }

    var wordCount: Int {
        transcriptEn.split(separator: " ").count
    }

    var statusLabel: String {
        switch status {
        case "speaking":     return "🎙 Interviewer đang nói..."
        case "transcribing": return "✦ Đang nhận dạng..."
        case "disconnected": return "Mất kết nối"
        default:             return "Đang chờ..."
        }
    }
}
