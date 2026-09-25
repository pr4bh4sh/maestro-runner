import Foundation
import XCTest

/// Handles Gesture.* RPCs: tap, doubleTap, longPress, swipe, scroll.
final class GestureHandler {
    private let snapshotManager: SnapshotManager
    private weak var sessionHandler: SessionHandler?

    init(snapshotManager: SnapshotManager, sessionHandler: SessionHandler) {
        self.snapshotManager = snapshotManager
        self.sessionHandler = sessionHandler
    }

    func handle(method: String, request: Request) throws -> AnyCodable? {
        switch method {
        case "Gesture.tap":
            return try tap(request)
        case "Gesture.doubleTap":
            return try doubleTap(request)
        case "Gesture.longPress":
            return try longPress(request)
        case "Gesture.swipe":
            return try swipe(request)
        case "Gesture.scroll":
            return try scroll(request)
        case "Gesture.findAndTap":
            return try findAndTap(request)
        default:
            throw HandlerError.unknownMethod(method)
        }
    }

    // MARK: - Tap at coordinates

    private func tap(_ request: Request) throws -> AnyCodable {
        guard let x = request.double("x"), let y = request.double("y") else {
            throw HandlerError.missingParam("x, y")
        }

        guard let app = sessionHandler?.getApp() else {
            throw HandlerError.invalidParam("No active session")
        }

        let normalized = app.coordinate(withNormalizedOffset: .zero)
        let point = normalized.withOffset(CGVector(dx: x, dy: y))
        point.tap()

        snapshotManager.invalidate()
        return AnyCodable(["success": true])
    }

    // MARK: - Double tap

    private func doubleTap(_ request: Request) throws -> AnyCodable {
        guard let x = request.double("x"), let y = request.double("y") else {
            throw HandlerError.missingParam("x, y")
        }

        guard let app = sessionHandler?.getApp() else {
            throw HandlerError.invalidParam("No active session")
        }

        let normalized = app.coordinate(withNormalizedOffset: .zero)
        let point = normalized.withOffset(CGVector(dx: x, dy: y))
        point.doubleTap()

        snapshotManager.invalidate()
        return AnyCodable(["success": true])
    }

    // MARK: - Long press

    private func longPress(_ request: Request) throws -> AnyCodable {
        guard let x = request.double("x"), let y = request.double("y") else {
            throw HandlerError.missingParam("x, y")
        }

        let duration = request.double("duration") ?? 1.0

        guard let app = sessionHandler?.getApp() else {
            throw HandlerError.invalidParam("No active session")
        }

        let normalized = app.coordinate(withNormalizedOffset: .zero)
        let point = normalized.withOffset(CGVector(dx: x, dy: y))
        point.press(forDuration: duration)

        snapshotManager.invalidate()
        return AnyCodable(["success": true])
    }

    // MARK: - Swipe

    private func swipe(_ request: Request) throws -> AnyCodable {
        guard let fromX = request.double("fromX"),
              let fromY = request.double("fromY"),
              let toX = request.double("toX"),
              let toY = request.double("toY") else {
            throw HandlerError.missingParam("fromX, fromY, toX, toY")
        }

        let duration = request.double("duration") ?? 0.3

        guard let app = sessionHandler?.getApp() else {
            throw HandlerError.invalidParam("No active session")
        }

        let normalized = app.coordinate(withNormalizedOffset: .zero)
        let from = normalized.withOffset(CGVector(dx: fromX, dy: fromY))
        let to = normalized.withOffset(CGVector(dx: toX, dy: toY))
        from.press(forDuration: 0.05, thenDragTo: to, withVelocity: .default, thenHoldForDuration: duration)

        snapshotManager.invalidate()
        return AnyCodable(["success": true])
    }

    // MARK: - Scroll

    private func scroll(_ request: Request) throws -> AnyCodable {
        guard let direction = request.string("direction") else {
            throw HandlerError.missingParam("direction")
        }

        let screenSize = sessionHandler?.screenSize ?? CGSize(width: 390, height: 844)
        let centerX = screenSize.width / 2
        let centerY = screenSize.height / 2
        let scrollDist = screenSize.height / 3

        guard let app = sessionHandler?.getApp() else {
            throw HandlerError.invalidParam("No active session")
        }

        let normalized = app.coordinate(withNormalizedOffset: .zero)
        let fromPt: CGVector
        let toPt: CGVector

        switch direction.lowercased() {
        case "down":
            // Scroll down = reveal content below = swipe UP
            fromPt = CGVector(dx: centerX, dy: centerY + scrollDist / 2)
            toPt = CGVector(dx: centerX, dy: centerY - scrollDist / 2)
        case "up":
            // Scroll up = reveal content above = swipe DOWN
            fromPt = CGVector(dx: centerX, dy: centerY - scrollDist / 2)
            toPt = CGVector(dx: centerX, dy: centerY + scrollDist / 2)
        case "left":
            fromPt = CGVector(dx: centerX + scrollDist / 2, dy: centerY)
            toPt = CGVector(dx: centerX - scrollDist / 2, dy: centerY)
        case "right":
            fromPt = CGVector(dx: centerX - scrollDist / 2, dy: centerY)
            toPt = CGVector(dx: centerX + scrollDist / 2, dy: centerY)
        default:
            throw HandlerError.invalidParam("direction must be up, down, left, or right")
        }

        let from = normalized.withOffset(fromPt)
        let to = normalized.withOffset(toPt)
        from.press(forDuration: 0.05, thenDragTo: to)

        snapshotManager.invalidate()
        return AnyCodable(["success": true])
    }

    // MARK: - Combined find + tap (single RPC)

    private func findAndTap(_ request: Request) throws -> AnyCodable {
        let elements = try snapshotManager.elements()

        var target: ElementModel?

        if let text = request.string("text") {
            target = ElementTree.findForTap(elements, text: text)
        } else if let id = request.string("id") {
            let visible = ElementTree.filterVisible(elements)
            let matches = ElementTree.findByID(visible, id: id)
            target = ElementTree.sortClickableFirst(matches).first
        }

        guard let elem = target else {
            throw HandlerError.elementNotFound
        }

        guard let app = sessionHandler?.getApp() else {
            throw HandlerError.invalidParam("No active session")
        }

        // For text fields, use XCTest's native element tap to ensure proper focus.
        // Coordinate-based taps don't always trigger keyboard focus.
        if elem.elementType == .textField || elem.elementType == .secureTextField ||
           elem.elementType == .searchField || elem.elementType == .textView {
            let query: XCUIElementQuery
            switch elem.elementType {
            case .secureTextField: query = app.secureTextFields
            case .searchField: query = app.searchFields
            case .textView: query = app.textViews
            default: query = app.textFields
            }

            // Try to find and tap using XCTest native element query
            // This ensures proper keyboard focus activation
            let candidates = query.allElementsBoundByIndex
            for i in 0..<candidates.count {
                let field = candidates[i]
                if field.frame.intersects(elem.frame) && field.exists {
                    field.tap()
                    snapshotManager.invalidate()
                    return AnyCodable(elem.toDict())
                }
            }
        }

        // Default: coordinate-based tap (works for buttons, labels, etc.)
        let centerX = elem.frame.midX
        let centerY = elem.frame.midY
        let normalized = app.coordinate(withNormalizedOffset: .zero)
        let point = normalized.withOffset(CGVector(dx: centerX, dy: centerY))
        point.tap()

        snapshotManager.invalidate()
        return AnyCodable(elem.toDict())
    }
}
