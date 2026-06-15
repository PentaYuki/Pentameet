//
//  TranslationService.swift
//  Pentameet
//
//  Wraps Apple's Translation framework (TranslationSession) for on-device translation.
//  Provides debounced, queue-based translation of incremental text chunks.
//

import Foundation
import Translation

// MARK: - Translation Service

@Observable
final class TranslationService {

    // MARK: Published State

    /// The latest translated text.
    var lastTranslatedText: String = ""

    /// Full accumulated translated text.
    var fullTranslatedText: String = ""

    /// Whether translation is ready (session obtained).
    var isReady: Bool = false

    /// Error message.
    var errorMessage: String?

    // MARK: Callback

    /// Called when a new translation chunk is ready.
    var onTranslated: ((String) -> Void)?

    // MARK: Configuration

    /// Translation session configuration for SwiftUI .translationTask modifier.
    var configuration: TranslationSession.Configuration?

    // MARK: Private

    private var session: TranslationSession?
    private var pendingText: String = ""
    private var debounceTask: Task<Void, Never>?
    private let debounceInterval: TimeInterval
    private var lastTranslateTime = Date()

    /// Queue to serialize translation requests.
    private let translationQueue = DispatchQueue(label: "pentameet.translation", qos: .userInitiated)
    private var isTranslating = false

    // MARK: Init

    /// - Parameter debounceInterval: Seconds to wait before sending accumulated text for translation.
    ///   Shorter = more responsive, longer = better translation quality (more context).
    init(
        sourceLanguage: Locale.Language = Locale.Language(identifier: "en"),
        targetLanguage: Locale.Language = Locale.Language(identifier: "vi"),
        debounceInterval: TimeInterval = 0.4
    ) {
        self.debounceInterval = debounceInterval
        self.configuration = TranslationSession.Configuration(
            source: sourceLanguage,
            target: targetLanguage
        )
    }

    // MARK: - Session Management

    /// Called from SwiftUI's .translationTask modifier to provide the session.
    func setSession(_ session: TranslationSession) {
        self.session = session
        self.isReady = true
        self.errorMessage = nil
    }

    /// Invalidate and re-create the session (e.g., when changing languages).
    func invalidateSession() {
        session = nil
        isReady = false
        // Toggling configuration triggers SwiftUI to re-create the session
        configuration?.invalidate()
    }

    /// Update translation languages and invalidate current session.
    func updateLanguages(source: String, target: String) {
        self.configuration = TranslationSession.Configuration(
            source: Locale.Language(identifier: source),
            target: Locale.Language(identifier: target)
        )
        invalidateSession()
    }

    // MARK: - Public API

    /// Queue text for translation. Text is batched and translated on sentence boundaries or timeouts.
    func translate(delta: String) {
        pendingText += (pendingText.isEmpty ? "" : " ") + delta

        // Check if delta contains punctuation that marks a clause/sentence boundary
        let hasBoundary = delta.contains(where: { [".", ",", "?", "!", ";", ":"].contains($0) })
        let timeSinceLastTranslate = Date().timeIntervalSince(lastTranslateTime)

        // If we hit a punctuation boundary, or if it has been more than 1.0 second since the last translation
        if hasBoundary || timeSinceLastTranslate >= 1.0 {
            // Cancel any pending timeout task
            debounceTask?.cancel()
            debounceTask = nil
            
            let textToTranslate = pendingText
            pendingText = ""
            
            guard !textToTranslate.isEmpty else { return }
            
            lastTranslateTime = Date()
            Task { @MainActor [weak self] in
                await self?.performTranslation(textToTranslate)
            }
        } else {
            // Otherwise, set/refresh a timeout task to translate after 1.0 second of inactivity
            debounceTask?.cancel()
            debounceTask = Task { @MainActor [weak self] in
                guard let self else { return }
                try? await Task.sleep(for: .seconds(1))
                
                guard !Task.isCancelled else { return }
                
                let textToTranslate = self.pendingText
                self.pendingText = ""
                
                guard !textToTranslate.isEmpty else { return }
                
                self.lastTranslateTime = Date()
                await self.performTranslation(textToTranslate)
            }
        }
    }

    /// Translate immediately without debounce (e.g., when pipeline stops).
    func flushPending() async {
        debounceTask?.cancel()
        let text = pendingText
        pendingText = ""
        guard !text.isEmpty else { return }
        await performTranslation(text)
    }

    /// Reset all state.
    func reset() {
        debounceTask?.cancel()
        pendingText = ""
        lastTranslatedText = ""
        fullTranslatedText = ""
    }

    // MARK: - Translation Execution

    private func performTranslation(_ text: String) async {
        guard let session else {
            errorMessage = "Translation session chưa sẵn sàng. Vui lòng đợi tải model ngôn ngữ."
            return
        }

        do {
            let response = try await session.translate(text)
            let translated = response.targetText

            await MainActor.run {
                self.lastTranslatedText = translated
                self.fullTranslatedText += (self.fullTranslatedText.isEmpty ? "" : " ") + translated
                self.errorMessage = nil
                self.onTranslated?(translated)
            }
        } catch {
            await MainActor.run {
                self.errorMessage = "Lỗi dịch: \(error.localizedDescription)"
            }
        }
    }
}
