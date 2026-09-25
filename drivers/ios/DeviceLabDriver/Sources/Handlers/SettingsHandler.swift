import Foundation
import XCTest

/// Handles Settings.* RPCs: timeouts, quiescence, alert action.
final class SettingsHandler {
    private weak var sessionHandler: SessionHandler?

    /// Find timeout in milliseconds.
    var findTimeout: Int = 17000

    /// Wait for idle timeout in milliseconds (0 = disabled).
    var waitForIdleTimeout: Int = 0

    init(sessionHandler: SessionHandler) {
        self.sessionHandler = sessionHandler
    }

    func handle(method: String, request: Request) throws -> AnyCodable? {
        switch method {
        case "Settings.update":
            return try update(request)
        case "Settings.get":
            return try get(request)
        case "Settings.setAlertAction":
            return try setAlertAction(request)
        case "Settings.setFindTimeout":
            return try setFindTimeout(request)
        case "Settings.setWaitForIdleTimeout":
            return try setIdleTimeout(request)
        default:
            throw HandlerError.unknownMethod(method)
        }
    }

    private func update(_ request: Request) throws -> AnyCodable {
        if let timeout = request.int("findTimeout") {
            findTimeout = timeout
        }
        if let timeout = request.int("waitForIdleTimeout") {
            waitForIdleTimeout = timeout
        }
        if let action = request.string("alertAction") {
            sessionHandler?.alertAction = action
        }
        return AnyCodable(["success": true])
    }

    private func get(_ request: Request) throws -> AnyCodable {
        return AnyCodable([
            "findTimeout": findTimeout,
            "waitForIdleTimeout": waitForIdleTimeout,
            "alertAction": sessionHandler?.alertAction ?? "",
        ] as [String: Any])
    }

    private func setAlertAction(_ request: Request) throws -> AnyCodable {
        guard let action = request.string("action") else {
            throw HandlerError.missingParam("action")
        }
        sessionHandler?.alertAction = action
        return AnyCodable(["success": true, "alertAction": action])
    }

    private func setFindTimeout(_ request: Request) throws -> AnyCodable {
        guard let timeout = request.int("timeout") else {
            throw HandlerError.missingParam("timeout")
        }
        findTimeout = timeout
        return AnyCodable(["success": true, "findTimeout": timeout])
    }

    private func setIdleTimeout(_ request: Request) throws -> AnyCodable {
        guard let timeout = request.int("timeout") else {
            throw HandlerError.missingParam("timeout")
        }
        waitForIdleTimeout = timeout
        return AnyCodable(["success": true, "waitForIdleTimeout": timeout])
    }
}
