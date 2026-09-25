import Foundation
import XCTest

/// Handles Session.* and Alert.* RPCs.
final class SessionHandler {
    private let snapshotManager: SnapshotManager
    private var app: XCUIApplication?
    private var sessionActive = false

    /// Alert auto-handling action: "accept", "dismiss", or "" (none).
    var alertAction: String = ""

    /// Cached screen size.
    var screenSize: CGSize = .zero

    init(snapshotManager: SnapshotManager) {
        self.snapshotManager = snapshotManager
    }

    func handle(method: String, request: Request) throws -> AnyCodable? {
        switch method {
        case "Session.create":
            return try createSession(request)
        case "Session.status":
            return AnyCodable(["active": sessionActive])
        case "Session.delete":
            sessionActive = false
            return AnyCodable(["deleted": true])
        default:
            throw HandlerError.unknownMethod(method)
        }
    }

    func handleAlert(method: String, request: Request) throws -> AnyCodable? {
        switch method {
        case "Alert.accept":
            return try handleAlertAction(accept: true)
        case "Alert.dismiss":
            return try handleAlertAction(accept: false)
        default:
            throw HandlerError.unknownMethod(method)
        }
    }

    // MARK: - Session

    private func createSession(_ request: Request) throws -> AnyCodable {
        guard let bundleID = request.string("bundleId") ?? request.string("bundleID") else {
            throw HandlerError.missingParam("bundleId")
        }

        let newApp = XCUIApplication(bundleIdentifier: bundleID)

        // Set alert action
        if let action = request.string("alertAction") {
            alertAction = action
        }

        // Setup alert auto-handling
        if alertAction == "accept" || alertAction == "dismiss" {
            setupAlertMonitor(accept: alertAction == "accept")
        }

        // Launch arguments
        if let args = request.stringArray("launchArguments") {
            newApp.launchArguments = args
        }

        // Launch environment
        if let env = request.dict("launchEnvironment") {
            var envDict: [String: String] = [:]
            for (k, v) in env {
                envDict[k] = "\(v)"
            }
            newApp.launchEnvironment = envDict
        }

        newApp.launch()
        app = newApp
        snapshotManager.setApp(newApp)
        sessionActive = true

        // Get screen size
        let mainScreen = XCUIScreen.main
        screenSize = mainScreen.screenshot().image.size
        snapshotManager.screenSize = screenSize

        return AnyCodable([
            "sessionId": bundleID,
            "deviceInfo": [
                "platformVersion": UIDevice.current.systemVersion,
                "model": UIDevice.current.model,
                "displaySize": "\(Int(screenSize.width))x\(Int(screenSize.height))",
            ] as [String: Any],
        ])
    }

    // MARK: - Alert handling

    private var alertMonitorToken: NSObjectProtocol?

    private func setupAlertMonitor(accept: Bool) {
        // XCTest UI interruption monitor for permission dialogs
        alertMonitorToken = addUIInterruptionMonitor(withDescription: "Permission Alert") { alert in
            if accept {
                let allowButton = alert.buttons["Allow"]
                let allowWhileUsing = alert.buttons["Allow While Using App"]
                if allowWhileUsing.exists {
                    allowWhileUsing.tap()
                } else if allowButton.exists {
                    allowButton.tap()
                } else {
                    // Try the first button as fallback
                    let buttons = alert.buttons
                    if buttons.count > 0 {
                        buttons.element(boundBy: buttons.count - 1).tap()
                    }
                }
            } else {
                let dontAllowButton = alert.buttons["Don\u{2019}t Allow"]
                let dontAllow = alert.buttons["Don't Allow"]
                if dontAllowButton.exists {
                    dontAllowButton.tap()
                } else if dontAllow.exists {
                    dontAllow.tap()
                } else {
                    alert.buttons.element(boundBy: 0).tap()
                }
            }
            return true
        }
    }

    private func handleAlertAction(accept: Bool) throws -> AnyCodable {
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let alerts = springboard.alerts
        guard alerts.count > 0 else {
            throw HandlerError.elementNotFound
        }
        let alert = alerts.firstMatch
        if accept {
            let allow = alert.buttons["Allow"]
            let allowWhile = alert.buttons["Allow While Using App"]
            let ok = alert.buttons["OK"]
            if allowWhile.exists { allowWhile.tap() }
            else if allow.exists { allow.tap() }
            else if ok.exists { ok.tap() }
            else {
                let buttons = alert.buttons
                if buttons.count > 0 {
                    buttons.element(boundBy: buttons.count - 1).tap()
                }
            }
        } else {
            let dontAllow = alert.buttons["Don\u{2019}t Allow"]
            let cancel = alert.buttons["Cancel"]
            if dontAllow.exists { dontAllow.tap() }
            else if cancel.exists { cancel.tap() }
            else {
                alert.buttons.element(boundBy: 0).tap()
            }
        }
        snapshotManager.invalidate()
        return AnyCodable(["success": true])
    }

    /// Get the current app.
    func getApp() -> XCUIApplication? { return app }
}

// UIInterruptionMonitor is a class method on XCTestCase, but we need it in our runner.
// The DeviceLabDriverRunner (XCTestCase subclass) will call setupAlertMonitor.
// For now, the addUIInterruptionMonitor call will be available in the test context.
private func addUIInterruptionMonitor(withDescription description: String, handler: @escaping (XCUIElement) -> Bool) -> NSObjectProtocol? {
    // This function is available in XCTest UI test context
    // It's a method on XCTestCase, so we'll wire it through the runner
    return nil
}
