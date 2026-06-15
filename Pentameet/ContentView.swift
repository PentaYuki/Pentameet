//
//  ContentView.swift
//  Pentameet
//
//  Main UI: Device picker, Start/Stop control, live transcript panels,
//  and translation status. Hosts the .translationTask modifier.
//

import SwiftUI
@preconcurrency import Translation

struct ContentView: View {
    @State private var pipeline = TranslationPipeline()
    @State private var showSettings = false
    @State private var autoScroll = true

    var body: some View {
        ZStack {
            // Background gradient
            LinearGradient(
                colors: [
                    Color(hue: 0.72, saturation: 0.35, brightness: 0.12),
                    Color(hue: 0.68, saturation: 0.25, brightness: 0.18),
                    Color(hue: 0.60, saturation: 0.20, brightness: 0.10)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(spacing: 0) {
                // Header
                headerView

                Divider()
                    .background(Color.white.opacity(0.1))

                // Main content
                HStack(spacing: 0) {
                    // Original transcript panel
                    transcriptPanel(
                        title: "🎤 Gốc (\(pipeline.sourceLanguage.name))",
                        text: pipeline.speechEngine.fullTranscript,
                        entries: pipeline.transcriptEntries.map { ($0.timeString, $0.original) },
                        accentColor: Color(hue: 0.58, saturation: 0.6, brightness: 0.85)
                    )

                    // Divider
                    Rectangle()
                        .fill(Color.white.opacity(0.08))
                        .frame(width: 1)

                    // Translated panel
                    transcriptPanel(
                        title: "📝 Dịch (\(pipeline.targetLanguage.name))",
                        text: pipeline.translationService.fullTranslatedText,
                        entries: pipeline.transcriptEntries.compactMap { entry in
                            guard let translated = entry.translated else { return nil }
                            return (entry.timeString, translated)
                        },
                        accentColor: Color(hue: 0.0, saturation: 0.6, brightness: 0.9)
                    )
                }

                Divider()
                    .background(Color.white.opacity(0.1))

                // Status bar
                statusBar
            }
        }
        .frame(minWidth: 800, minHeight: 500)
        // Translation framework session provider
        .translationTask(pipeline.translationService.configuration) { session in
            pipeline.translationService.setSession(session)
        }
    }

    // MARK: - Header

    private var headerView: some View {
        HStack(spacing: 16) {
            // App icon
            Image(systemName: "waveform.circle.fill")
                .font(.system(size: 28))
                .foregroundStyle(
                    LinearGradient(
                        colors: [
                            Color(hue: 0.8, saturation: 0.7, brightness: 0.95),
                            Color(hue: 0.6, saturation: 0.7, brightness: 0.9)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .symbolEffect(.pulse, isActive: pipeline.state == .running)

            Text("PentaMeet")
                .font(.system(size: 20, weight: .bold, design: .rounded))
                .foregroundStyle(.white)

            Spacer()

            // Device picker
            devicePicker

            // Main control button
            controlButton

            // Settings
            Button {
                showSettings.toggle()
            } label: {
                Image(systemName: "gearshape.fill")
                    .font(.system(size: 14))
                    .foregroundStyle(.white.opacity(0.7))
            }
            .buttonStyle(.plain)
            .popover(isPresented: $showSettings) {
                settingsView
            }

            // Clear button
            Button {
                pipeline.clearAll()
            } label: {
                Image(systemName: "trash")
                    .font(.system(size: 13))
                    .foregroundStyle(.white.opacity(0.5))
            }
            .buttonStyle(.plain)
            .help("Xóa tất cả transcript")
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
        .background(.ultraThinMaterial.opacity(0.3))
    }

    // MARK: - Device Picker

    private var devicePicker: some View {
        Menu {
            ForEach(pipeline.audioManager.availableInputDevices) { device in
                Button {
                    pipeline.selectDevice(device)
                } label: {
                    HStack {
                        if device.isBlackHole {
                            Image(systemName: "waveform.path")
                        } else {
                            Image(systemName: "mic")
                        }
                        Text(device.name)
                        if device.id == pipeline.audioManager.selectedDevice?.id {
                            Image(systemName: "checkmark")
                        }
                    }
                }
            }

            if pipeline.audioManager.availableInputDevices.isEmpty {
                Text("Không tìm thấy thiết bị âm thanh")
            }

            Divider()

            Button("Làm mới danh sách") {
                pipeline.audioManager.refreshDevices()
            }
        } label: {
            HStack(spacing: 6) {
                Image(systemName: pipeline.audioManager.selectedDevice?.isBlackHole == true
                      ? "waveform.path" : "mic.fill")
                    .font(.system(size: 11))

                Text(pipeline.audioManager.selectedDevice?.name ?? "Chọn thiết bị")
                    .font(.system(size: 12, weight: .medium))
                    .lineLimit(1)

                Image(systemName: "chevron.down")
                    .font(.system(size: 9, weight: .semibold))
            }
            .foregroundStyle(.white.opacity(0.8))
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(.white.opacity(0.08))
                    .stroke(.white.opacity(0.15), lineWidth: 1)
            )
        }
        .menuStyle(.borderlessButton)
        .fixedSize()
    }

    // MARK: - Control Button

    private var controlButton: some View {
        Button {
            withAnimation(.spring(response: 0.3)) {
                pipeline.toggle()
            }
        } label: {
            HStack(spacing: 6) {
                Image(systemName: pipeline.state.isActive ? "stop.fill" : "play.fill")
                    .font(.system(size: 12))
                Text(pipeline.state.isActive ? "Dừng" : "Bắt đầu")
                    .font(.system(size: 13, weight: .semibold))
            }
            .foregroundStyle(.white)
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(
                        pipeline.state.isActive
                        ? LinearGradient(colors: [.red.opacity(0.8), .red.opacity(0.6)], startPoint: .top, endPoint: .bottom)
                        : LinearGradient(
                            colors: [
                                Color(hue: 0.55, saturation: 0.7, brightness: 0.8),
                                Color(hue: 0.65, saturation: 0.7, brightness: 0.7)
                            ],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
            )
            .shadow(color: pipeline.state.isActive ? .red.opacity(0.3) : .cyan.opacity(0.3), radius: 8, y: 2)
        }
        .buttonStyle(.plain)
    }

    // MARK: - Transcript Panel

    private func transcriptPanel(
        title: String,
        text: String,
        entries: [(String, String)],
        accentColor: Color
    ) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            // Panel header
            HStack {
                Text(title)
                    .font(.system(size: 13, weight: .semibold, design: .rounded))
                    .foregroundStyle(accentColor)

                Spacer()

                if !text.isEmpty {
                    Button {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(text, forType: .string)
                    } label: {
                        Image(systemName: "doc.on.doc")
                            .font(.system(size: 11))
                            .foregroundStyle(.white.opacity(0.4))
                    }
                    .buttonStyle(.plain)
                    .help("Sao chép toàn bộ")
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(Color.white.opacity(0.03))

            // Entries
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 4) {
                        ForEach(Array(entries.enumerated()), id: \.offset) { index, entry in
                            HStack(alignment: .top, spacing: 8) {
                                Text(entry.0)
                                    .font(.system(size: 10, design: .monospaced))
                                    .foregroundStyle(.white.opacity(0.3))
                                    .frame(width: 55, alignment: .trailing)

                                Text(entry.1)
                                    .font(.system(size: 14, weight: .regular))
                                    .foregroundStyle(.white.opacity(0.9))
                                    .textSelection(.enabled)
                            }
                            .id(index)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 3)
                            .transition(.opacity.combined(with: .move(edge: .bottom)))
                        }
                    }
                    .padding(.vertical, 8)
                }
                .onChange(of: entries.count) { _, _ in
                    if autoScroll, let last = entries.indices.last {
                        withAnimation(.easeOut(duration: 0.2)) {
                            proxy.scrollTo(last, anchor: .bottom)
                        }
                    }
                }
            }

            // Empty state
            if entries.isEmpty {
                VStack(spacing: 8) {
                    Spacer()
                    Image(systemName: "text.bubble")
                        .font(.system(size: 32))
                        .foregroundStyle(.white.opacity(0.15))
                    Text("Chưa có nội dung")
                        .font(.system(size: 13))
                        .foregroundStyle(.white.opacity(0.25))
                    Spacer()
                }
                .frame(maxWidth: .infinity)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Status Bar

    private var statusBar: some View {
        HStack(spacing: 12) {
            // Pipeline state indicator
            HStack(spacing: 6) {
                Circle()
                    .fill(stateColor)
                    .frame(width: 8, height: 8)
                    .shadow(color: stateColor.opacity(0.6), radius: 4)

                Text(pipeline.state.displayText)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(.white.opacity(0.6))
            }

            if pipeline.state == .running {
                // Live indicator
                HStack(spacing: 4) {
                    Image(systemName: "waveform")
                        .font(.system(size: 10))
                        .foregroundStyle(.green.opacity(0.7))
                        .symbolEffect(.variableColor.iterative, isActive: true)

                    Text("LIVE")
                        .font(.system(size: 9, weight: .bold, design: .monospaced))
                        .foregroundStyle(.green.opacity(0.7))
                }
            }

            Spacer()

            // Translation status
            if !pipeline.translationService.isReady {
                HStack(spacing: 4) {
                    ProgressView()
                        .scaleEffect(0.5)
                    Text("Đang tải model dịch...")
                        .font(.system(size: 11))
                        .foregroundStyle(.yellow.opacity(0.7))
                }
            }

            // TTS indicator
            if pipeline.ttsManager.isSpeaking {
                HStack(spacing: 4) {
                    Image(systemName: "speaker.wave.2.fill")
                        .font(.system(size: 10))
                        .foregroundStyle(.cyan.opacity(0.7))
                        .symbolEffect(.variableColor.iterative, isActive: true)
                    Text("Đang đọc...")
                        .font(.system(size: 11))
                        .foregroundStyle(.cyan.opacity(0.7))
                }
            }

            // Error display
            if let error = pipeline.speechEngine.errorMessage ?? pipeline.translationService.errorMessage {
                Text(error)
                    .font(.system(size: 10))
                    .foregroundStyle(.red.opacity(0.8))
                    .lineLimit(1)
            }

            // Entry count
            Text("\(pipeline.transcriptEntries.count) mục")
                .font(.system(size: 11, design: .monospaced))
                .foregroundStyle(.white.opacity(0.35))
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(.ultraThinMaterial.opacity(0.2))
    }

    // MARK: - Settings View

    private var settingsView: some View {
        let tts = pipeline.ttsManager
        return VStack(alignment: .leading, spacing: 16) {
            Text("Cài đặt")
                .font(.headline)

            GroupBox("Giọng đọc (TTS)") {
                VStack(alignment: .leading, spacing: 10) {
                    HStack {
                        Text("Tốc độ:")
                            .font(.system(size: 12))
                        Slider(
                            value: Binding(
                                get: { tts.speechRate },
                                set: { tts.speechRate = $0 }
                            ),
                            in: 0.1...0.75,
                            step: 0.05
                        )
                        Text(String(format: "%.2f", tts.speechRate))
                            .font(.system(size: 11, design: .monospaced))
                            .frame(width: 35)
                    }

                    HStack {
                        Text("Cao độ:")
                            .font(.system(size: 12))
                        Slider(
                            value: Binding(
                                get: { tts.pitchMultiplier },
                                set: { tts.pitchMultiplier = $0 }
                            ),
                            in: 0.5...2.0,
                            step: 0.05
                        )
                        Text(String(format: "%.2f", tts.pitchMultiplier))
                            .font(.system(size: 11, design: .monospaced))
                            .frame(width: 35)
                    }

                    Toggle("Chế độ ngắt (interrupt)", isOn: Binding(
                        get: { tts.interruptMode },
                        set: { tts.interruptMode = $0 }
                    ))
                        .font(.system(size: 12))
                }
                .padding(4)
            }

            GroupBox("Dịch thuật") {
                VStack(alignment: .leading, spacing: 10) {
                    Toggle("Tự động cuộn", isOn: $autoScroll)
                        .font(.system(size: 12))

                    Divider()
                        .padding(.vertical, 2)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Ngôn ngữ nguồn (Nói):")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(.secondary)
                        Picker("", selection: $pipeline.sourceLanguage) {
                            ForEach(TranslationPipeline.availableLanguages) { lang in
                                Text(lang.name).tag(lang)
                            }
                        }
                        .labelsHidden()
                        .pickerStyle(.menu)
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Ngôn ngữ đích (Dịch):")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(.secondary)
                        Picker("", selection: $pipeline.targetLanguage) {
                            ForEach(TranslationPipeline.availableLanguages) { lang in
                                Text(lang.name).tag(lang)
                            }
                        }
                        .labelsHidden()
                        .pickerStyle(.menu)
                    }
                }
                .padding(4)
            }
        }
        .padding(16)
        .frame(width: 300)
    }

    // MARK: - Helpers

    private var stateColor: Color {
        switch pipeline.state {
        case .idle: return .gray
        case .starting: return .yellow
        case .running: return .green
        case .stopping: return .orange
        case .error: return .red
        }
    }
}

#Preview {
    ContentView()
}
