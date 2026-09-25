import Foundation
import XCTest

/// Handles Input.* RPCs: typeText, eraseText, clearText, pressKey.
final class InputHandler {
    private let snapshotManager: SnapshotManager
    private weak var sessionHandler: SessionHandler?

    init(snapshotManager: SnapshotManager, sessionHandler: SessionHandler) {
        self.snapshotManager = snapshotManager
        self.sessionHandler = sessionHandler
    }

    func handle(method: String, request: Request) throws -> AnyCodable? {
        switch method {
        case "Input.typeText":
            return try typeText(request)
        case "Input.eraseText":
            return try eraseText(request)
        case "Input.clearText":
            return try clearText(request)
        case "Input.pressKey":
            return try pressKey(request)
        case "Input.hideKeyboard":
            return try hideKeyboard(request)
        default:
            throw HandlerError.unknownMethod(method)
        }
    }

    // MARK: - Text input via event synthesis

    /// Types text using XCPointerEventPath (same low-level API as WDA).
    /// Does NOT require keyboard focus. Returns NSError on failure.
    /// No keyboard wait needed — EventSynthesizer sends events through the
    /// XCTest daemon event pipeline, not through the software keyboard.
    private func synthesizeText(_ text: String) throws {
        if let error = EventSynthesizer.typeText(text) {
            throw HandlerError.invalidParam("typeText failed: \(error.localizedDescription)")
        }
    }

    // MARK: - Type Text

    private func typeText(_ request: Request) throws -> AnyCodable {
        guard let text = request.string("text") else {
            throw HandlerError.missingParam("text")
        }

        guard sessionHandler?.getApp() != nil else {
            throw HandlerError.invalidParam("No active session")
        }

        try synthesizeText(text)

        snapshotManager.invalidate()
        return AnyCodable(["success": true, "text": text])
    }

    // MARK: - Erase Text

    private func eraseText(_ request: Request) throws -> AnyCodable {
        let count = request.int("count") ?? 50

        guard sessionHandler?.getApp() != nil else {
            throw HandlerError.invalidParam("No active session")
        }

        let deleteString = String(repeating: XCUIKeyboardKey.delete.rawValue, count: count)
        try synthesizeText(deleteString)

        snapshotManager.invalidate()
        return AnyCodable(["success": true, "count": count])
    }

    // MARK: - Clear Text

    private func clearText(_ request: Request) throws -> AnyCodable {
        guard sessionHandler?.getApp() != nil else {
            throw HandlerError.invalidParam("No active session")
        }

        let deleteString = String(repeating: XCUIKeyboardKey.delete.rawValue, count: 100)
        try synthesizeText(deleteString)

        snapshotManager.invalidate()
        return AnyCodable(["success": true])
    }

    // MARK: - Press Key

    private func pressKey(_ request: Request) throws -> AnyCodable {
        guard let key = request.string("key") else {
            throw HandlerError.missingParam("key")
        }

        guard sessionHandler?.getApp() != nil else {
            throw HandlerError.invalidParam("No active session")
        }

        switch key.lowercased() {
        case "return", "enter":
            try synthesizeText("\n")
        case "tab":
            try synthesizeText("\t")
        case "delete", "backspace":
            try synthesizeText(XCUIKeyboardKey.delete.rawValue)
        case "space":
            try synthesizeText(" ")
        case "home":
            XCUIDevice.shared.press(.home)
        default:
            if key.count == 1 {
                try synthesizeText(key)
            } else {
                throw HandlerError.invalidParam("Unknown key: \(key)")
            }
        }

        snapshotManager.invalidate()
        return AnyCodable(["success": true, "key": key])
    }

    // MARK: - Hide Keyboard

    private func hideKeyboard(_ request: Request) throws -> AnyCodable {
        guard sessionHandler?.getApp() != nil else {
            throw HandlerError.invalidParam("No active session")
        }

        try synthesizeText("\n")

        snapshotManager.invalidate()
        return AnyCodable(["success": true])
    }
}
