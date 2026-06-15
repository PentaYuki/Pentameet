//
//  SpeechRecognitionEngine.swift
//  Pentameet
//
//  Streaming speech-to-text using SFSpeechRecognizer with delta extraction.
//  Only emits newly recognized words, not the full transcript from the beginning.
//
//  Fixes applied:
//  - Issue 1: Sets input device via AudioUnit (app-local, no system-wide change)
//  - Issue 2: Recognition callback dispatched to main thread for thread safety
//

import Foundation
import Speech
import AVFoundation
import CoreAudio
import AudioToolbox

// MARK: - Speech Recognition Engine

@Observable
final class SpeechRecognitionEngine {

    // MARK: Published State

    /// The full transcript accumulated so far.
    var fullTranscript: String = ""

    /// The latest delta (newly recognized words).
    var latestDelta: String = ""

    /// Whether recognition is currently active.
    var isRecognizing: Bool = false

    /// Flag to temporarily ignore input buffers (e.g., when TTS is speaking).
    var ignoreInput: Bool = false

    /// Error message if something goes wrong.
    var errorMessage: String?

    // MARK: Callback

    /// Called each time new text is recognized (delta only).
    var onNewText: ((String) -> Void)?

    // MARK: Private

    private let audioEngine = AVAudioEngine()
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private var speechRecognizer: SFSpeechRecognizer?

    /// Tracks what text has already been processed.
    private var lastProcessedText: String = ""

    /// Source language locale.
    var sourceLocale: Locale

    /// The audio device ID to use (e.g., BlackHole). nil = system default.
    private var inputDeviceID: AudioDeviceID?

    // MARK: Init

    init(sourceLocale: Locale = Locale(identifier: "en-US")) {
        self.sourceLocale = sourceLocale
    }

    // MARK: - Public API

    /// Request authorization and start recognition.
    /// - Parameter deviceID: Optional specific audio device ID (e.g., BlackHole).
    ///   If nil, uses the system default input device.
    func start(inputDeviceID: AudioDeviceID? = nil) {
        self.inputDeviceID = inputDeviceID
        requestAuthorization { [weak self] authorized in
            guard let self else { return }
            if authorized {
                do {
                    try self.startRecognition()
                } catch {
                    self.errorMessage = "Không thể bắt đầu nhận dạng: \(error.localizedDescription)"
                }
            } else {
                self.errorMessage = "Chưa được cấp quyền Speech Recognition"
            }
        }
    }

    /// Stop recognition and clean up.
    func stop() {
        isRecognizing = false
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionTask?.cancel()
        recognitionRequest = nil
        recognitionTask = nil
    }

    /// Reset transcript (e.g., when starting a new session).
    func resetTranscript() {
        fullTranscript = ""
        latestDelta = ""
        lastProcessedText = ""
    }

    // MARK: - Authorization

    private func requestAuthorization(completion: @escaping (Bool) -> Void) {
        SFSpeechRecognizer.requestAuthorization { status in
            DispatchQueue.main.async {
                switch status {
                case .authorized:
                    completion(true)
                case .denied:
                    self.errorMessage = "Speech recognition bị từ chối. Vui lòng bật trong System Settings → Privacy."
                    completion(false)
                case .restricted:
                    self.errorMessage = "Speech recognition bị giới hạn trên thiết bị này."
                    completion(false)
                case .notDetermined:
                    self.errorMessage = "Chưa xác định quyền Speech Recognition."
                    completion(false)
                @unknown default:
                    completion(false)
                }
            }
        }
    }

    // MARK: - Input Device (Issue 1 Fix)

    /// Set the audio input device on AVAudioEngine's underlying AudioUnit.
    /// This is app-local — does NOT change the system default input device.
    private func configureInputDevice(_ deviceID: AudioDeviceID) throws {
        let inputNode = audioEngine.inputNode

        guard let audioUnit = inputNode.audioUnit else {
            throw NSError(
                domain: "PentaMeet",
                code: -1,
                userInfo: [NSLocalizedDescriptionKey: "AudioUnit chưa sẵn sàng. Không thể set input device."]
            )
        }

        var devID = deviceID
        let status = AudioUnitSetProperty(
            audioUnit,
            kAudioOutputUnitProperty_CurrentDevice,
            kAudioUnitScope_Global,
            0,
            &devID,
            UInt32(MemoryLayout<AudioDeviceID>.size)
        )

        guard status == noErr else {
            throw NSError(
                domain: NSOSStatusErrorDomain,
                code: Int(status),
                userInfo: [NSLocalizedDescriptionKey: "Không thể set input device (lỗi: \(status))"]
            )
        }
    }

    // MARK: - Recognition

    private func startRecognition() throws {
        // Cancel any existing task
        recognitionTask?.cancel()
        recognitionTask = nil

        // Configure speech recognizer
        speechRecognizer = SFSpeechRecognizer(locale: sourceLocale)
        guard let speechRecognizer, speechRecognizer.isAvailable else {
            errorMessage = "Speech recognizer không khả dụng cho locale: \(sourceLocale.identifier)"
            return
        }

        // Create recognition request
        let request = SFSpeechAudioBufferRecognitionRequest()
        request.shouldReportPartialResults = true
        request.requiresOnDeviceRecognition = false

        if #available(macOS 13, *) {
            request.addsPunctuation = true
        }

        self.recognitionRequest = request

        // Set specific input device BEFORE installing tap
        if let deviceID = inputDeviceID {
            do {
                try configureInputDevice(deviceID)
                audioEngine.reset()
            } catch {
                errorMessage = "Lỗi âm thanh: \(error.localizedDescription)\nBạn hãy đổi đầu vào hệ thống thành BlackHole và chọn 'Mặc định hệ thống' trong ứng dụng."
                isRecognizing = false
                return
            }
        }

        // Install audio tap
        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)

        // Prevent nullptr == Tap() crash by removing any existing tap first
        inputNode.removeTap(onBus: 0)

        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { [weak self] buffer, _ in
            guard let self else { return }
            if !self.ignoreInput {
                self.recognitionRequest?.append(buffer)
            }
        }

        // Start audio engine
        audioEngine.prepare()
        try audioEngine.start()

        // Reset delta tracking
        lastProcessedText = ""

        // Start recognition task
        // [Issue 2 Fix] Callback dispatched to main thread for @Observable thread safety
        recognitionTask = speechRecognizer.recognitionTask(with: request) { [weak self] result, error in
            DispatchQueue.main.async {
                guard let self else { return }

                if let result {
                    self.processResult(result)
                }

                if let error {
                    // Recognition timed out or encountered an error
                    let nsError = error as NSError

                    // Error code 1110 = "No speech detected" / timeout — auto-restart
                    // Error code 301 = recognition request was cancelled — don't restart
                    if nsError.code == 1110 {
                        self.restartRecognition()
                    } else if nsError.code != 301 {
                        self.errorMessage = "Lỗi nhận dạng: \(error.localizedDescription)"
                        self.isRecognizing = false
                    }
                }

                if result?.isFinal == true {
                    // Session ended, restart for continuous recognition
                    self.restartRecognition()
                }
            }
        }

        isRecognizing = true
        errorMessage = nil
    }

    // MARK: - Delta Extraction

    private func processResult(_ result: SFSpeechRecognitionResult) {
        let currentText = result.bestTranscription.formattedString

        // Helper to check if a character is normalized (keeps letters and numbers, lowercases them)
        func normalizeChar(_ char: Character) -> String {
            return char.lowercased().filter { $0.isLetter || $0.isNumber }
        }

        // Map characters to their original indices in the string
        struct CharMap {
            let normChar: String // empty if it was filtered out (punctuation, space, etc.)
            let origIndex: String.Index
        }

        var currentMap: [CharMap] = []
        for index in currentText.indices {
            let char = currentText[index]
            currentMap.append(CharMap(normChar: normalizeChar(char), origIndex: index))
        }

        var lastMap: [CharMap] = []
        for index in lastProcessedText.indices {
            let char = lastProcessedText[index]
            lastMap.append(CharMap(normChar: normalizeChar(char), origIndex: index))
        }

        // Filter out non-alphanumeric elements to get the clean normalized streams
        let currentNormOnly = currentMap.filter { !$0.normChar.isEmpty }
        let lastNormOnly = lastMap.filter { !$0.normChar.isEmpty }

        // Find the number of matching normalized characters from the start
        var matchCount = 0
        while matchCount < lastNormOnly.count && matchCount < currentNormOnly.count {
            if lastNormOnly[matchCount].normChar == currentNormOnly[matchCount].normChar {
                matchCount += 1
            } else {
                break
            }
        }

        // Extract the delta substring by mapping the matchCount back to the original index
        let deltaText: String
        if matchCount > 0 {
            // Get the element corresponding to the last matched normalized character
            let lastMatchedElement = currentNormOnly[matchCount - 1]
            // The delta text starts at the index immediately after lastMatchedElement.origIndex
            if let nextIndex = currentText.index(lastMatchedElement.origIndex, offsetBy: 1, limitedBy: currentText.endIndex) {
                deltaText = String(currentText[nextIndex...])
            } else {
                deltaText = ""
            }
        } else {
            // No matches at the start, treat the whole current text as delta
            deltaText = currentText
        }

        // Update full transcript
        fullTranscript = currentText

        // Only emit non-empty, non-whitespace-only deltas
        let trimmed = deltaText.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.isEmpty {
            latestDelta = trimmed
            lastProcessedText = currentText
            onNewText?(trimmed)
        }
    }

    // MARK: - Auto-Restart

    /// Restart recognition for continuous listening.
    /// SFSpeechRecognizer has a ~60 second limit per task.
    private func restartRecognition() {
        // Clean up current session
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionTask = nil
        recognitionRequest = nil

        // Brief delay before restarting to avoid rapid cycling
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { [weak self] in
            guard let self, self.isRecognizing else { return }
            do {
                try self.startRecognition()
            } catch {
                self.errorMessage = "Không thể khởi động lại: \(error.localizedDescription)"
                self.isRecognizing = false
            }
        }
    }
}
