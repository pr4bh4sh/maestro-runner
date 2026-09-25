import Foundation

// MARK: - Request / Response / Event

/// Incoming request from the Go host.
struct Request: Decodable {
    let id: Int64
    let method: String
    let params: [String: AnyCodable]?
}

/// Outgoing response matched by request ID.
struct Response: Encodable {
    let id: Int64
    var result: AnyCodable?
    var error: ErrorPayload?
}

/// Outgoing push event (unsolicited).
struct Event: Encodable {
    let event: String
    var params: AnyCodable?
}

/// Error detail inside a Response.
struct ErrorPayload: Codable {
    let code: String
    let message: String
}

// MARK: - Type-erased Codable wrapper

/// Minimal type-erased Codable for heterogeneous JSON values.
struct AnyCodable: Codable {
    let value: Any

    init(_ value: Any) { self.value = value }

    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { value = NSNull(); return }
        if let v = try? c.decode(Bool.self) { value = v; return }
        if let v = try? c.decode(Int64.self) { value = v; return }
        if let v = try? c.decode(Double.self) { value = v; return }
        if let v = try? c.decode(String.self) { value = v; return }
        if let v = try? c.decode([AnyCodable].self) { value = v.map(\.value); return }
        if let v = try? c.decode([String: AnyCodable].self) {
            value = v.mapValues(\.value); return
        }
        throw DecodingError.dataCorruptedError(in: c, debugDescription: "Unsupported JSON type")
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch value {
        case is NSNull:          try c.encodeNil()
        case let v as Bool:      try c.encode(v)
        case let v as Int:       try c.encode(v)
        case let v as Int64:     try c.encode(v)
        case let v as Double:    try c.encode(v)
        case let v as String:    try c.encode(v)
        case let v as [Any]:     try c.encode(v.map { AnyCodable($0) })
        case let v as [String: Any]: try c.encode(v.mapValues { AnyCodable($0) })
        default:                 try c.encode(String(describing: value))
        }
    }
}

// MARK: - Param helpers

extension Request {
    func string(_ key: String) -> String? {
        guard let p = params, let v = p[key]?.value as? String else { return nil }
        return v
    }

    func int(_ key: String) -> Int? {
        if let p = params, let v = p[key]?.value as? Int64 { return Int(v) }
        if let p = params, let v = p[key]?.value as? Int { return v }
        if let p = params, let v = p[key]?.value as? Double { return Int(v) }
        return nil
    }

    func double(_ key: String) -> Double? {
        if let p = params, let v = p[key]?.value as? Double { return v }
        if let p = params, let v = p[key]?.value as? Int64 { return Double(v) }
        if let p = params, let v = p[key]?.value as? Int { return Double(v) }
        return nil
    }

    func bool(_ key: String) -> Bool? {
        guard let p = params, let v = p[key]?.value as? Bool else { return nil }
        return v
    }

    func dict(_ key: String) -> [String: Any]? {
        guard let p = params, let v = p[key]?.value as? [String: Any] else { return nil }
        return v
    }

    func stringArray(_ key: String) -> [String]? {
        guard let p = params, let arr = p[key]?.value as? [Any] else { return nil }
        return arr.compactMap { $0 as? String }
    }
}
