//
//  TranslationPipeline.swift
//  Pentameet
//
//  Orchestrator that connects all components:
//  AudioEngine → STT → Delta Extract → Debounce → Translate → TTS Queue
//
//  Fix applied:
//  - Issue 3: Transcript entries created per translation batch (not per delta)
//    to correctly pair original text with its translation.
//

import Foundation
import CoreAudio

// MARK: - Pipeline State

enum PipelineState: Equatable {
    case idle
    case starting
    case running
    case stopping
    case error(String)

    var displayText: String {
        switch self {
        case .idle: return "Sẵn sàng"
        case .starting: return "Đang khởi động..."
        case .running: return "Đang chạy"
        case .stopping: return "Đang dừng..."
        case .error(let msg): return "Lỗi: \(msg)"
        }
    }

    var isActive: Bool {
        switch self {
        case .running, .starting: return true
        default: return false
        }
    }
}

// MARK: - Translation Pipeline

@Observable
final class TranslationPipeline {

    // MARK: Sub-components

    let audioManager = AudioDeviceManager()
    let speechEngine = SpeechRecognitionEngine()
    let translationService = TranslationService()
    let ttsManager = SpeechSynthesizerManager()

    // MARK: State

    var state: PipelineState = .idle

    /// Transcript log entries for display.
    var transcriptEntries: [TranscriptEntry] = []

    // MARK: Language Configuration

    var sourceLanguage: LanguageOption = TranslationPipeline.availableLanguages[0] {
        didSet {
            speechEngine.sourceLocale = Locale(identifier: sourceLanguage.localeIdentifier)
            updateTranslationConfiguration()
        }
    }

    var targetLanguage: LanguageOption = TranslationPipeline.availableLanguages[1] {
        didSet {
            updateTranslationConfiguration()
            ttsManager.voiceLanguage = targetLanguage.localeIdentifier
        }
    }

    static let availableLanguages: [LanguageOption] = [
        LanguageOption(localeIdentifier: "en-US", name: "🇺🇸 English (US)", translationCode: "en"),
        LanguageOption(localeIdentifier: "vi-VN", name: "🇻🇳 Tiếng Việt", translationCode: "vi"),
        LanguageOption(localeIdentifier: "ja-JP", name: "🇯🇵 日本語 (Japanese)", translationCode: "ja"),
        LanguageOption(localeIdentifier: "zh-CN", name: "🇨🇳 中文 (Chinese)", translationCode: "zh"),
        LanguageOption(localeIdentifier: "fr-FR", name: "🇫🇷 Français (French)", translationCode: "fr"),
        LanguageOption(localeIdentifier: "es-ES", name: "🇪🇸 Español (Spanish)", translationCode: "es"),
        LanguageOption(localeIdentifier: "ko-KR", name: "🇰🇷 한국어 (Korean)", translationCode: "ko"),
        LanguageOption(localeIdentifier: "de-DE", name: "🇩🇪 Deutsch (German)", translationCode: "de")
    ]

    // MARK: Private

    private func updateTranslationConfiguration() {
        translationService.updateLanguages(
            source: sourceLanguage.translationCode,
            target: targetLanguage.translationCode
        )
    }

    /// [Issue 3 Fix] Accumulates original text alongside TranslationService's debounce.
    /// When translation completes, this is paired with the translated text in a single entry.
    private var pendingOriginalText: String = ""

    /// Timestamp when the first delta of a pending batch arrived.
    private var pendingBatchTimestamp: Date?

    // MARK: Init

    init() {
        wireComponents()
    }

    // MARK: - Public API

    /// Start the full pipeline.
    func start() {
        guard !state.isActive else { return }

        state = .starting

        // Determine which device to use (nil = system default)
        let deviceID: AudioDeviceID?
        if let selected = audioManager.selectedDevice, selected.id != 0 {
            deviceID = selected.id
        } else {
            deviceID = nil
        }

        // Start speech recognition with the selected device
        speechEngine.start(inputDeviceID: deviceID)
        state = .running
    }

    /// Stop the full pipeline.
    func stop() {
        state = .stopping

        speechEngine.stop()
        ttsManager.stopAll()

        // Flush any pending translation
        Task {
            await translationService.flushPending()
            await MainActor.run {
                self.state = .idle
            }
        }
    }

    /// Toggle pipeline on/off.
    func toggle() {
        if state.isActive {
            stop()
        } else {
            start()
        }
    }

    /// Clear all transcripts and reset.
    func clearAll() {
        stop()
        speechEngine.resetTranscript()
        translationService.reset()
        transcriptEntries.removeAll()
        pendingOriginalText = ""
        pendingBatchTimestamp = nil
    }

    /// Select an audio input device.
    func selectDevice(_ device: AudioDevice) {
        let wasRunning = state.isActive
        if wasRunning { stop() }

        audioManager.selectDevice(device)

        if wasRunning {
            // Brief delay to let audio system settle
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { [weak self] in
                self?.start()
            }
        }
    }

    // MARK: - Wiring

    /// Connect sub-component callbacks to form the pipeline.
    private func wireComponents() {
        // STT → Translation: when new text is recognized, accumulate and send for translation
        speechEngine.onNewText = { [weak self] delta in
            guard let self else { return }

            // [Issue 3 Fix] Accumulate original text for this debounce batch
            if self.pendingBatchTimestamp == nil {
                self.pendingBatchTimestamp = Date()
            }
            self.pendingOriginalText += (self.pendingOriginalText.isEmpty ? "" : " ") + delta

            // Send delta to translation service (it will debounce internally)
            self.translationService.translate(delta: delta)
        }

        // Translation → TTS: when translation completes, create entry and speak
        translationService.onTranslated = { [weak self] translated in
            guard let self else { return }

            // [Issue 3 Fix] Create a single entry pairing the accumulated original with translation
            let entry = TranscriptEntry(
                original: self.pendingOriginalText,
                translated: translated,
                timestamp: self.pendingBatchTimestamp ?? Date()
            )
            self.transcriptEntries.append(entry)

            // Reset pending accumulator for the next batch
            self.pendingOriginalText = ""
            self.pendingBatchTimestamp = nil

            // Speak the translation
            self.ttsManager.speak(translated)
        }

        // TTS Speaking State → STT Input Gate: ignore microphone input when TTS is reading the translation
        ttsManager.onSpeakingStateChanged = { [weak self] isSpeaking in
            self?.speechEngine.ignoreInput = isSpeaking
        }
    }
}

// MARK: - Transcript Entry

struct TranscriptEntry: Identifiable {
    let id = UUID()
    let original: String
    var translated: String?
    let timestamp: Date

    var timeString: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        return formatter.string(from: timestamp)
    }
}

// MARK: - Language Option

struct LanguageOption: Identifiable, Hashable, Equatable {
    var id: String { localeIdentifier }
    let localeIdentifier: String
    let name: String
    let translationCode: String
}
