//
//  SpeechSynthesizerManager.swift
//  Pentameet
//
//  Queue-based TTS manager using AVSpeechSynthesizer.
//  Reads translated text chunks sequentially without interrupting.
//

import Foundation
import AVFoundation

// MARK: - Speech Synthesizer Manager

@Observable
final class SpeechSynthesizerManager: NSObject {

    // MARK: Published State

    /// Whether the synthesizer is currently speaking.
    var isSpeaking: Bool = false {
        didSet {
            if oldValue != isSpeaking {
                onSpeakingStateChanged?(isSpeaking)
            }
        }
    }

    /// The text currently being spoken.
    var currentUtterance: String = ""

    /// Number of items in the speech queue.
    var queueCount: Int = 0

    // MARK: Callbacks

    /// Called when the speaking state changes.
    var onSpeakingStateChanged: ((Bool) -> Void)?

    // MARK: Configuration

    /// The language/voice for TTS output.
    var voiceLanguage: String = "vi-VN"

    /// Speech rate (0.0 to 1.0). Default is about 0.5.
    var speechRate: Float = AVSpeechUtteranceDefaultSpeechRate

    /// Pitch multiplier (0.5 to 2.0). Default 1.0.
    var pitchMultiplier: Float = 1.05

    /// Volume (0.0 to 1.0).
    var volume: Float = 1.0

    /// If true, new text interrupts current speech. If false, queues sequentially.
    var interruptMode: Bool = false

    // MARK: Private

    private let synthesizer = AVSpeechSynthesizer()
    private var speechQueue: [String] = []
    private let queueLock = NSLock()

    // MARK: Init

    override init() {
        super.init()
        synthesizer.delegate = self
    }

    // MARK: - Public API

    /// Enqueue text for speaking.
    func speak(_ text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        // Filter out filler words / noise
        let filtered = filterFillerWords(trimmed)
        guard !filtered.isEmpty else { return }

        if interruptMode {
            // Stop current speech and speak new text immediately
            synthesizer.stopSpeaking(at: .immediate)
            queueLock.lock()
            speechQueue.removeAll()
            queueLock.unlock()
            speakNow(filtered)
        } else {
            // Queue-based: add to queue and process
            queueLock.lock()
            speechQueue.append(filtered)
            queueCount = speechQueue.count
            queueLock.unlock()

            if !synthesizer.isSpeaking {
                processNextInQueue()
            }
        }
    }

    /// Stop all speech and clear queue.
    func stopAll() {
        synthesizer.stopSpeaking(at: .immediate)
        queueLock.lock()
        speechQueue.removeAll()
        queueCount = 0
        queueLock.unlock()
        isSpeaking = false
        currentUtterance = ""
    }

    /// Pause current speech.
    func pause() {
        synthesizer.pauseSpeaking(at: .word)
    }

    /// Resume paused speech.
    func resume() {
        synthesizer.continueSpeaking()
    }

    // MARK: - Private

    private func speakNow(_ text: String) {
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: voiceLanguage)
        utterance.rate = speechRate
        utterance.pitchMultiplier = pitchMultiplier
        utterance.volume = volume
        // Small pre/post delay for natural pacing
        utterance.preUtteranceDelay = 0.05
        utterance.postUtteranceDelay = 0.1

        currentUtterance = text
        isSpeaking = true
        synthesizer.speak(utterance)
    }

    private func processNextInQueue() {
        queueLock.lock()
        guard !speechQueue.isEmpty else {
            queueCount = 0
            queueLock.unlock()
            isSpeaking = false
            currentUtterance = ""
            return
        }
        let next = speechQueue.removeFirst()
        queueCount = speechQueue.count
        queueLock.unlock()

        speakNow(next)
    }

    /// Filter out common filler words / noise that shouldn't be spoken.
    private func filterFillerWords(_ text: String) -> String {
        let fillers: Set<String> = ["um", "uh", "hmm", "hm", "ah", "er", "erm"]
        let words = text.split(separator: " ")
        let filtered = words.filter { !fillers.contains($0.lowercased()) }
        return filtered.joined(separator: " ")
    }
}

// MARK: - AVSpeechSynthesizerDelegate

extension SpeechSynthesizerManager: AVSpeechSynthesizerDelegate {

    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didFinish utterance: AVSpeechUtterance
    ) {
        DispatchQueue.main.async { [weak self] in
            self?.processNextInQueue()
        }
    }

    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didCancel utterance: AVSpeechUtterance
    ) {
        DispatchQueue.main.async { [weak self] in
            self?.isSpeaking = false
            self?.currentUtterance = ""
        }
    }
}
