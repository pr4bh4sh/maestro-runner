import Foundation

/// Dispatches incoming requests to the appropriate handler by method prefix.
final class RequestRouter {
    let session: SessionHandler
    let element: ElementHandler
    let gesture: GestureHandler
    let input: InputHandler
    let app: AppHandler
    let settings: SettingsHandler

    init(session: SessionHandler, element: ElementHandler, gesture: GestureHandler,
         input: InputHandler, app: AppHandler, settings: SettingsHandler) {
        self.session = session
        self.element = element
        self.gesture = gesture
        self.input = input
        self.app = app
        self.settings = settings
    }

    typealias JSONCallback = (Response) -> Void
    typealias BinaryCallback = (Int64, Data) -> Void

    /// Handle a request: dispatch to the correct handler and call back with the response.
    func handle(_ request: Request, sendJSON: @escaping JSONCallback, sendBinary: @escaping BinaryCallback) {
        // XCTest APIs (XCUIApplication, tap, typeText, snapshot, etc.) must run on
        // the main thread. Dispatch all handler work there. The WebSocket server
        // runs its receive loop on a Network.framework queue, so this won't deadlock.
        DispatchQueue.main.async { [self] in
            let method = request.method
            var response = Response(id: request.id)

            do {
                if method.hasPrefix("Session.") {
                    response.result = try session.handle(method: method, request: request)
                } else if method.hasPrefix("UI.") {
                    // UI.screenshot returns binary data
                    if method == "UI.screenshot" {
                        let jpegData = try element.screenshot()
                        sendBinary(request.id, jpegData)
                        return
                    }
                    response.result = try element.handle(method: method, request: request)
                } else if method.hasPrefix("Gesture.") {
                    response.result = try gesture.handle(method: method, request: request)
                } else if method.hasPrefix("Input.") {
                    response.result = try input.handle(method: method, request: request)
                } else if method.hasPrefix("Device.") || method.hasPrefix("App.") {
                    response.result = try app.handle(method: method, request: request)
                } else if method.hasPrefix("Settings.") {
                    response.result = try settings.handle(method: method, request: request)
                } else if method.hasPrefix("Alert.") {
                    response.result = try session.handleAlert(method: method, request: request)
                } else {
                    throw HandlerError.unknownMethod(method)
                }
            } catch {
                response.error = ErrorPayload(
                    code: "handler_error",
                    message: error.localizedDescription
                )
            }

            sendJSON(response)
        }
    }
}

enum HandlerError: LocalizedError {
    case unknownMethod(String)
    case missingParam(String)
    case invalidParam(String)
    case elementNotFound
    case notImplemented(String)

    var errorDescription: String? {
        switch self {
        case .unknownMethod(let m): return "Unknown method: \(m)"
        case .missingParam(let p): return "Missing parameter: \(p)"
        case .invalidParam(let p): return "Invalid parameter: \(p)"
        case .elementNotFound: return "Element not found"
        case .notImplemented(let m): return "Not implemented: \(m)"
        }
    }
}
