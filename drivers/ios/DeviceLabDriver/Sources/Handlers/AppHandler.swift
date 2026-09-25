import Foundation
import XCTest

/// Handles Device.* and App.* RPCs: launchApp, terminateApp, openURL, clipboard, orientation.
final class AppHandler {
    private let snapshotManager: SnapshotManager
    private weak var sessionHandler: SessionHandler?

    init(snapshotManager: SnapshotManager, sessionHandler: SessionHandler) {
        self.snapshotManager = snapshotManager
        self.sessionHandler = sessionHandler
    }

    func handle(method: String, request: Request) throws -> AnyCodable? {
        switch method {
        case "Device.launchApp", "App.launch":
            return try launchApp(request)
        case "Device.terminateApp", "App.terminate":
            return try terminateApp(request)
        case "Device.openURL":
            return try openURL(request)
        case "Device.getOrientation":
            return try getOrientation()
        case "Device.setOrientation":
            return try setOrientation(request)
        case "Device.getClipboard":
            return try getClipboard()
        case "Device.setClipboard":
            return try setClipboard(request)
        case "Device.pressHome":
            XCUIDevice.shared.press(.home)
            snapshotManager.invalidate()
            return AnyCodable(["success": true])
        case "Device.pressButton":
            return try pressButton(request)
        default:
            throw HandlerError.unknownMethod(method)
        }
    }

    // MARK: - Launch App

    private func launchApp(_ request: Request) throws -> AnyCodable {
        guard let bundleID = request.string("bundleId") ?? request.string("bundleID") else {
            throw HandlerError.missingParam("bundleId")
        }

        let app = XCUIApplication(bundleIdentifier: bundleID)

        if let args = request.stringArray("arguments") {
            app.launchArguments = args
        }
        if let env = request.dict("environment") {
            var envDict: [String: String] = [:]
            for (k, v) in env { envDict[k] = "\(v)" }
            app.launchEnvironment = envDict
        }

        app.launch()
        snapshotManager.setApp(app)

        return AnyCodable(["success": true, "bundleId": bundleID])
    }

    // MARK: - Terminate App

    private func terminateApp(_ request: Request) throws -> AnyCodable {
        guard let bundleID = request.string("bundleId") ?? request.string("bundleID") else {
            throw HandlerError.missingParam("bundleId")
        }

        let app = XCUIApplication(bundleIdentifier: bundleID)
        app.terminate()
        snapshotManager.invalidate()

        return AnyCodable(["success": true, "bundleId": bundleID])
    }

    // MARK: - Open URL

    private func openURL(_ request: Request) throws -> AnyCodable {
        guard let urlString = request.string("url") else {
            throw HandlerError.missingParam("url")
        }

        // Launch Safari with the URL
        let safari = XCUIApplication(bundleIdentifier: "com.apple.mobilesafari")
        safari.launch()

        // Wait a moment for Safari to be ready
        Thread.sleep(forTimeInterval: 0.5)

        // Type the URL into the address bar
        let addressBar = safari.textFields.firstMatch
        if addressBar.waitForExistence(timeout: 3) {
            addressBar.tap()
            addressBar.typeText(urlString + "\n")
        }

        snapshotManager.invalidate()
        return AnyCodable(["success": true, "url": urlString])
    }

    // MARK: - Orientation

    private func getOrientation() throws -> AnyCodable {
        let orientation: String
        switch XCUIDevice.shared.orientation {
        case .portrait, .portraitUpsideDown:
            orientation = "portrait"
        case .landscapeLeft, .landscapeRight:
            orientation = "landscape"
        default:
            orientation = "portrait"
        }
        return AnyCodable(["orientation": orientation])
    }

    private func setOrientation(_ request: Request) throws -> AnyCodable {
        guard let orientation = request.string("orientation") else {
            throw HandlerError.missingParam("orientation")
        }

        switch orientation.lowercased() {
        case "portrait":
            XCUIDevice.shared.orientation = .portrait
        case "landscape", "landscapeleft":
            XCUIDevice.shared.orientation = .landscapeLeft
        case "landscaperight":
            XCUIDevice.shared.orientation = .landscapeRight
        default:
            throw HandlerError.invalidParam("Unknown orientation: \(orientation)")
        }

        snapshotManager.invalidate()
        return AnyCodable(["success": true, "orientation": orientation])
    }

    // MARK: - Clipboard

    private func getClipboard() throws -> AnyCodable {
        let text = UIPasteboard.general.string ?? ""
        return AnyCodable(["text": text])
    }

    private func setClipboard(_ request: Request) throws -> AnyCodable {
        guard let text = request.string("text") else {
            throw HandlerError.missingParam("text")
        }
        UIPasteboard.general.string = text
        return AnyCodable(["success": true])
    }

    // MARK: - Hardware Buttons

    private func pressButton(_ request: Request) throws -> AnyCodable {
        guard let button = request.string("button") else {
            throw HandlerError.missingParam("button")
        }

        switch button.lowercased() {
        case "home":
            XCUIDevice.shared.press(.home)
        #if !targetEnvironment(simulator)
        case "volumeup":
            XCUIDevice.shared.press(.volumeUp)
        case "volumedown":
            XCUIDevice.shared.press(.volumeDown)
        #endif
        default:
            throw HandlerError.invalidParam("Unknown button: \(button)")
        }

        snapshotManager.invalidate()
        return AnyCodable(["success": true, "button": button])
    }
}
