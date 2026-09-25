import Foundation
import XCTest

/// Handles UI.* RPCs: findElement, getSource, screenshot.
final class ElementHandler {
    private let snapshotManager: SnapshotManager
    private weak var sessionHandler: SessionHandler?

    init(snapshotManager: SnapshotManager, sessionHandler: SessionHandler) {
        self.snapshotManager = snapshotManager
        self.sessionHandler = sessionHandler
    }

    func handle(method: String, request: Request) throws -> AnyCodable? {
        switch method {
        case "UI.findElement":
            return try findElement(request)
        case "UI.getSource":
            return try getSource(request)
        case "UI.getKeyboardInfo":
            return try getKeyboardInfo()
        case "UI.hasFocusedElement":
            return try hasFocusedElement()
        default:
            throw HandlerError.unknownMethod(method)
        }
    }

    // MARK: - Screenshot (binary)

    func screenshot() throws -> Data {
        let screenshot = XCUIScreen.main.screenshot()
        guard let jpegData = screenshot.image.jpegData(compressionQuality: 0.8) else {
            throw HandlerError.invalidParam("Failed to encode screenshot as JPEG")
        }
        return jpegData
    }

    // MARK: - Find Element

    private func findElement(_ request: Request) throws -> AnyCodable {
        let elements = try snapshotManager.elements()

        // Search by text
        if let text = request.string("text") {
            let visible = ElementTree.filterVisible(elements)
            let matches = ElementTree.findByText(visible, text: text)

            if matches.isEmpty {
                throw HandlerError.elementNotFound
            }

            // Apply index
            let index = request.int("index") ?? 0
            let sorted = ElementTree.sortClickableFirst(matches)
            let selected: ElementModel
            if index > 0 && index < sorted.count {
                selected = sorted[index]
            } else {
                selected = sorted[0]
            }

            return AnyCodable(selected.toDict())
        }

        // Search by accessibility ID
        if let id = request.string("id") {
            let visible = ElementTree.filterVisible(elements)
            let matches = ElementTree.findByID(visible, id: id)

            if matches.isEmpty {
                throw HandlerError.elementNotFound
            }

            let index = request.int("index") ?? 0
            let sorted = ElementTree.sortClickableFirst(matches)
            let selected: ElementModel
            if index > 0 && index < sorted.count {
                selected = sorted[index]
            } else {
                selected = sorted[0]
            }

            return AnyCodable(selected.toDict())
        }

        // Search by type
        if let type = request.string("type") {
            let visible = ElementTree.filterVisible(elements)
            let matches = ElementTree.findByType(visible, type: type)

            if matches.isEmpty {
                throw HandlerError.elementNotFound
            }

            return AnyCodable(matches[0].toDict())
        }

        throw HandlerError.missingParam("text, id, or type")
    }

    // MARK: - Get Source (XML)

    private func getSource(_ request: Request) throws -> AnyCodable {
        let snap = try snapshotManager.rawSnapshot()
        let screenSize = sessionHandler?.screenSize ?? CGSize(width: 390, height: 844)
        let xml = ElementTree.snapshotToXML(snap, screenSize: screenSize)
        return AnyCodable(["xml": xml])
    }

    // MARK: - Keyboard Info

    private func getKeyboardInfo() throws -> AnyCodable {
        guard let app = sessionHandler?.getApp() else {
            return AnyCodable(["visible": false])
        }
        let keyboards = app.keyboards
        let visible = keyboards.count > 0 && keyboards.firstMatch.exists
        return AnyCodable(["visible": visible])
    }

    // MARK: - Focus Check

    private func hasFocusedElement() throws -> AnyCodable {
        let elements = try snapshotManager.elements()
        let focused = elements.contains { $0.hasFocus }
        return AnyCodable(["focused": focused])
    }
}
