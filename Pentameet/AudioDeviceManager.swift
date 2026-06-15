//
//  AudioDeviceManager.swift
//  Pentameet
//
//  Manages audio input device enumeration and selection via Core Audio HAL.
//  Allows programmatic selection of BlackHole or any virtual audio device.
//
//  NOTE: This manager ONLY enumerates devices and tracks selection.
//  It does NOT change the system default input device.
//  The actual device binding is done in SpeechRecognitionEngine via AudioUnit.
//

import Foundation
import CoreAudio
import AVFoundation

// MARK: - Audio Device Model

struct AudioDevice: Identifiable, Hashable {
    let id: AudioDeviceID
    let name: String
    let uid: String
    let hasInput: Bool

    var isBlackHole: Bool {
        name.localizedCaseInsensitiveContains("BlackHole")
    }

    static var systemDefault: AudioDevice {
        AudioDevice(id: 0, name: "Mặc định hệ thống (System Default)", uid: "default", hasInput: true)
    }
}

// MARK: - Audio Device Manager

@Observable
final class AudioDeviceManager {

    // MARK: Published State

    var availableInputDevices: [AudioDevice] = []
    var selectedDevice: AudioDevice?
    var errorMessage: String?

    // MARK: Private

    private var listenerBlock: AudioObjectPropertyListenerBlock?

    // MARK: Init

    init() {
        refreshDevices()
        installDeviceChangeListener()
    }

    deinit {
        removeDeviceChangeListener()
    }

    // MARK: - Public API

    /// Refresh the list of available audio input devices.
    func refreshDevices() {
        let devices = enumerateInputDevices()
        availableInputDevices = [AudioDevice.systemDefault] + devices

        // Auto-select "System Default" if nothing is selected or selected device disappeared
        if selectedDevice == nil {
            selectedDevice = AudioDevice.systemDefault
        }
        if let sel = selectedDevice, !availableInputDevices.contains(where: { $0.id == sel.id }) {
            selectedDevice = AudioDevice.systemDefault
        }
    }

    /// Select a specific audio device (just updates the selection, does NOT change system default).
    func selectDevice(_ device: AudioDevice) {
        selectedDevice = device
        errorMessage = nil
    }

    /// Find BlackHole device automatically.
    func findBlackHoleDevice() -> AudioDevice? {
        return availableInputDevices.first(where: { $0.isBlackHole })
    }

    // MARK: - Core Audio Enumeration

    private func enumerateInputDevices() -> [AudioDevice] {
        var propertyAddress = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )

        var dataSize: UInt32 = 0
        var status = AudioObjectGetPropertyDataSize(
            AudioObjectID(kAudioObjectSystemObject),
            &propertyAddress,
            0, nil,
            &dataSize
        )
        guard status == noErr else { return [] }

        let deviceCount = Int(dataSize) / MemoryLayout<AudioDeviceID>.size
        var deviceIDs = [AudioDeviceID](repeating: 0, count: deviceCount)

        status = AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &propertyAddress,
            0, nil,
            &dataSize,
            &deviceIDs
        )
        guard status == noErr else { return [] }

        return deviceIDs.compactMap { deviceID -> AudioDevice? in
            guard let name = getDeviceName(deviceID: deviceID),
                  let uid = getDeviceUID(deviceID: deviceID) else {
                return nil
            }

            let hasInput = deviceHasInputStreams(deviceID: deviceID)
            guard hasInput else { return nil }

            return AudioDevice(id: deviceID, name: name, uid: uid, hasInput: hasInput)
        }
    }

    private func getDeviceName(deviceID: AudioDeviceID) -> String? {
        var propertyAddress = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyDeviceNameCFString,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )

        var name: CFString = "" as CFString
        var dataSize = UInt32(MemoryLayout<CFString>.size)

        let status = AudioObjectGetPropertyData(
            deviceID,
            &propertyAddress,
            0, nil,
            &dataSize,
            &name
        )

        return status == noErr ? (name as String) : nil
    }

    private func getDeviceUID(deviceID: AudioDeviceID) -> String? {
        var propertyAddress = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyDeviceUID,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )

        var uid: CFString = "" as CFString
        var dataSize = UInt32(MemoryLayout<CFString>.size)

        let status = AudioObjectGetPropertyData(
            deviceID,
            &propertyAddress,
            0, nil,
            &dataSize,
            &uid
        )

        return status == noErr ? (uid as String) : nil
    }

    private func deviceHasInputStreams(deviceID: AudioDeviceID) -> Bool {
        var propertyAddress = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyStreams,
            mScope: kAudioObjectPropertyScopeInput,
            mElement: kAudioObjectPropertyElementMain
        )

        var dataSize: UInt32 = 0
        let status = AudioObjectGetPropertyDataSize(
            deviceID,
            &propertyAddress,
            0, nil,
            &dataSize
        )

        return status == noErr && dataSize > 0
    }

    // MARK: - Device Change Listener

    private func installDeviceChangeListener() {
        var propertyAddress = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )

        let block: AudioObjectPropertyListenerBlock = { [weak self] _, _ in
            DispatchQueue.main.async {
                self?.refreshDevices()
            }
        }
        self.listenerBlock = block

        AudioObjectAddPropertyListenerBlock(
            AudioObjectID(kAudioObjectSystemObject),
            &propertyAddress,
            DispatchQueue.main,
            block
        )
    }

    private func removeDeviceChangeListener() {
        guard let block = listenerBlock else { return }
        var propertyAddress = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )

        AudioObjectRemovePropertyListenerBlock(
            AudioObjectID(kAudioObjectSystemObject),
            &propertyAddress,
            DispatchQueue.main,
            block
        )
    }
}
