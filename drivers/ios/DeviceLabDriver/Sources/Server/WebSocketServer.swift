import Foundation
import Network

/// Single-client WebSocket server using NWListener (Network.framework).
/// Zero external dependencies — ships with iOS 13+.
final class WebSocketServer {
    private var listener: NWListener?
    private var connection: NWConnection?
    private let port: UInt16
    private let queue = DispatchQueue(label: "com.devicelab.ws", qos: .userInteractive)
    private let router: RequestRouter

    /// Called when a client connects and the server is ready.
    var onReady: (() -> Void)?

    init(port: UInt16, router: RequestRouter) {
        self.port = port
        self.router = router
    }

    /// Start listening. Blocks until the listener is cancelled.
    func start() throws {
        let params = NWParameters.tcp
        let wsOptions = NWProtocolWebSocket.Options()
        wsOptions.autoReplyPing = true
        params.defaultProtocolStack.applicationProtocols.insert(wsOptions, at: 0)

        guard let nwPort = NWEndpoint.Port(rawValue: port) else {
            throw ServerError.invalidPort
        }

        let listener = try NWListener(using: params, on: nwPort)
        self.listener = listener

        listener.stateUpdateHandler = { [weak self] state in
            switch state {
            case .ready:
                NSLog("[DeviceLabDriver] WebSocket server listening on port \(self?.port ?? 0)")
            case .failed(let error):
                NSLog("[DeviceLabDriver] Listener failed: \(error)")
            default:
                break
            }
        }

        listener.newConnectionHandler = { [weak self] conn in
            self?.handleConnection(conn)
        }

        listener.start(queue: queue)
    }

    func stop() {
        connection?.cancel()
        listener?.cancel()
    }

    // MARK: - Connection handling

    private func handleConnection(_ conn: NWConnection) {
        // Single client — replace existing
        connection?.cancel()
        connection = conn

        conn.stateUpdateHandler = { [weak self] state in
            switch state {
            case .ready:
                NSLog("[DeviceLabDriver] Client connected")
                self?.onReady?()
                self?.receiveMessages(conn)
            case .failed(let error):
                NSLog("[DeviceLabDriver] Connection failed: \(error)")
            case .cancelled:
                NSLog("[DeviceLabDriver] Connection cancelled")
            default:
                break
            }
        }

        conn.start(queue: queue)
    }

    private func receiveMessages(_ conn: NWConnection) {
        conn.receiveMessage { [weak self] data, context, _, error in
            guard let self = self else { return }

            if let error = error {
                NSLog("[DeviceLabDriver] Receive error: \(error)")
                return
            }

            if let data = data, !data.isEmpty {
                self.handleMessage(data, context: context, on: conn)
            }

            // Continue receiving
            self.receiveMessages(conn)
        }
    }

    private func handleMessage(_ data: Data, context: NWConnection.ContentContext?, on conn: NWConnection) {
        // Check if it's a WebSocket text message
        let isText = context?.protocolMetadata(definition: NWProtocolWebSocket.definition)
            .flatMap { $0 as? NWProtocolWebSocket.Metadata }
            .map { $0.opcode == .text } ?? true

        guard isText else {
            NSLog("[DeviceLabDriver] Ignoring non-text frame")
            return
        }

        // Parse request
        let decoder = JSONDecoder()
        guard let request = try? decoder.decode(Request.self, from: data) else {
            NSLog("[DeviceLabDriver] Failed to decode request: \(String(data: data, encoding: .utf8) ?? "?")")
            return
        }

        // Route and handle
        router.handle(request) { [weak self] response in
            self?.sendResponse(response, on: conn)
        } sendBinary: { [weak self] id, binaryData in
            self?.sendBinaryResponse(id: id, data: binaryData, on: conn)
        }
    }

    // MARK: - Send

    private func sendResponse(_ response: Response, on conn: NWConnection) {
        let encoder = JSONEncoder()
        guard let data = try? encoder.encode(response) else {
            NSLog("[DeviceLabDriver] Failed to encode response")
            return
        }

        let metadata = NWProtocolWebSocket.Metadata(opcode: .text)
        let context = NWConnection.ContentContext(identifier: "text", metadata: [metadata])

        conn.send(content: data, contentContext: context, isComplete: true, completion: .contentProcessed { error in
            if let error = error {
                NSLog("[DeviceLabDriver] Send error: \(error)")
            }
        })
    }

    private func sendBinaryResponse(id: Int64, data: Data, on conn: NWConnection) {
        // Binary frame format: [8-byte big-endian request ID][raw payload]
        var frame = Data(count: 8)
        var bigEndianID = id.bigEndian
        withUnsafeBytes(of: &bigEndianID) { frame.replaceSubrange(0..<8, with: $0) }
        frame.append(data)

        let metadata = NWProtocolWebSocket.Metadata(opcode: .binary)
        let context = NWConnection.ContentContext(identifier: "binary", metadata: [metadata])

        conn.send(content: frame, contentContext: context, isComplete: true, completion: .contentProcessed { error in
            if let error = error {
                NSLog("[DeviceLabDriver] Binary send error: \(error)")
            }
        })
    }

    /// Send an event (unsolicited push message).
    func sendEvent(_ event: Event) {
        guard let conn = connection else { return }
        let encoder = JSONEncoder()
        guard let data = try? encoder.encode(event) else { return }

        let metadata = NWProtocolWebSocket.Metadata(opcode: .text)
        let context = NWConnection.ContentContext(identifier: "event", metadata: [metadata])

        conn.send(content: data, contentContext: context, isComplete: true, completion: .contentProcessed { _ in })
    }
}

enum ServerError: Error {
    case invalidPort
}
