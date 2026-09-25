import XCTest

/// XCTest UI test runner that starts a WebSocket server and blocks forever.
/// The Go host communicates with this process via WebSocket RPCs.
final class DeviceLabDriverRunner: XCTestCase {

    /// Main test method — starts the WS server and blocks until terminated.
    func testRunner() throws {
        // Critical: allow the test to continue after XCTest assertion failures.
        // Without this, errors like "Neither element nor any descendant has keyboard focus"
        // from typeText() would kill the entire test runner process.
        continueAfterFailure = true

        let port = serverPort()
        NSLog("[DeviceLabDriver] Starting on port \(port)")

        // Use Settings app as a dummy — it will be replaced on Session.create with the actual app.
        // We must use an explicit bundleIdentifier: the no-arg XCUIApplication()
        // requires UITargetAppBundleIdentifier in the xctestrun plist.
        let dummyApp = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        let snapshotManager = SnapshotManager(app: dummyApp)

        // Create handlers
        let sessionHandler = SessionHandler(snapshotManager: snapshotManager)
        let elementHandler = ElementHandler(snapshotManager: snapshotManager, sessionHandler: sessionHandler)
        let gestureHandler = GestureHandler(snapshotManager: snapshotManager, sessionHandler: sessionHandler)
        let inputHandler = InputHandler(snapshotManager: snapshotManager, sessionHandler: sessionHandler)
        let appHandler = AppHandler(snapshotManager: snapshotManager, sessionHandler: sessionHandler)
        let settingsHandler = SettingsHandler(sessionHandler: sessionHandler)

        // Create router
        let router = RequestRouter(
            session: sessionHandler,
            element: elementHandler,
            gesture: gestureHandler,
            input: inputHandler,
            app: appHandler,
            settings: settingsHandler
        )

        // Create and start WebSocket server
        let server = WebSocketServer(port: port, router: router)
        server.onReady = {
            NSLog("[DeviceLabDriver] WebSocket client connected — ready for commands")
        }

        do {
            try server.start()
        } catch {
            XCTFail("Failed to start WebSocket server: \(error)")
            return
        }

        NSLog("[DeviceLabDriver] ServerURLHere->ws://127.0.0.1:\(port)/ws")

        // Setup UI interruption monitor for permission alerts
        addUIInterruptionMonitor(withDescription: "Permission Alert") { alert in
            let action = sessionHandler.alertAction
            if action == "accept" {
                let allowWhile = alert.buttons["Allow While Using App"]
                let allow = alert.buttons["Allow"]
                let ok = alert.buttons["OK"]
                if allowWhile.exists { allowWhile.tap(); return true }
                if allow.exists { allow.tap(); return true }
                if ok.exists { ok.tap(); return true }
                let buttons = alert.buttons
                if buttons.count > 0 {
                    buttons.element(boundBy: buttons.count - 1).tap()
                    return true
                }
            } else if action == "dismiss" {
                let dontAllow = alert.buttons["Don\u{2019}t Allow"]
                let cancel = alert.buttons["Cancel"]
                if dontAllow.exists { dontAllow.tap(); return true }
                if cancel.exists { cancel.tap(); return true }
                alert.buttons.element(boundBy: 0).tap()
                return true
            }
            return false
        }

        // Keep the main thread alive using the run loop. This allows
        // DispatchQueue.main.async blocks (from the request router) to
        // execute — XCTest APIs must be called on the main thread.
        // A semaphore.wait() would block main and starve those dispatches.
        RunLoop.main.run()
    }

    /// Read the server port from the USE_PORT environment variable.
    /// Injected into the xctestrun plist by the Go runner.
    private func serverPort() -> UInt16 {
        if let portStr = ProcessInfo.processInfo.environment["USE_PORT"],
           let port = UInt16(portStr) {
            return port
        }
        return 9100 // default
    }
}
