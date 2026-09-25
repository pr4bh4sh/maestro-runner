import Foundation
import XCTest

/// Manages XCUIApplication snapshots with structural hash caching.
/// One `app.snapshot()` call captures the entire accessibility tree.
/// The hash is invalidated after any mutation (tap, type, swipe).
final class SnapshotManager {
    private var app: XCUIApplication
    private var cachedSnapshot: XCUIElementSnapshot?
    private var cachedElements: [ElementModel]?
    private var cachedHash: UInt64 = 0
    private let lock = NSLock()

    /// Screen size for visibility checks.
    var screenSize: CGSize = .zero

    init(app: XCUIApplication) {
        self.app = app
    }

    /// Update the target application (called when Session.create launches the real app).
    func setApp(_ newApp: XCUIApplication) {
        lock.lock()
        defer { lock.unlock() }
        app = newApp
        cachedSnapshot = nil
        cachedElements = nil
        cachedHash = 0
    }

    /// Get the current snapshot, using cache if the UI hasn't changed.
    func snapshot() throws -> XCUIElementSnapshot {
        lock.lock()
        defer { lock.unlock() }

        let snap = try app.snapshot()
        let hash = structuralHash(snap)

        if hash == cachedHash, let cached = cachedSnapshot {
            return cached
        }

        cachedSnapshot = snap
        cachedElements = nil // Invalidate flattened cache
        cachedHash = hash
        return snap
    }

    /// Get flattened elements from the current snapshot.
    func elements() throws -> [ElementModel] {
        lock.lock()
        defer { lock.unlock() }

        let snap = try app.snapshot()
        let hash = structuralHash(snap)

        if hash == cachedHash, let cached = cachedElements {
            return cached
        }

        cachedSnapshot = snap
        cachedHash = hash
        let elems = ElementTree.flatten(snap)
        cachedElements = elems
        return elems
    }

    /// Get the raw snapshot for XML serialization.
    func rawSnapshot() throws -> XCUIElementSnapshot {
        return try app.snapshot()
    }

    /// Invalidate the cache after a mutation (tap, type, swipe, etc.).
    func invalidate() {
        lock.lock()
        defer { lock.unlock() }
        cachedSnapshot = nil
        cachedElements = nil
        cachedHash = 0
    }

    // MARK: - Structural hash

    /// Compute a structural hash of text + class + state, ignoring bounds.
    /// This means we can skip re-snapshot if only bounds changed (e.g., scroll offset).
    private func structuralHash(_ snap: XCUIElementSnapshot) -> UInt64 {
        var hasher = FNV1aHasher()
        hashElement(snap, into: &hasher)
        return hasher.value
    }

    private func hashElement(_ snap: XCUIElementSnapshot, into hasher: inout FNV1aHasher) {
        hasher.combine(snap.elementType.rawValue)
        hasher.combine(snap.label ?? "")
        hasher.combine((snap.value as? String) ?? "")
        hasher.combine(snap.identifier)
        hasher.combine(snap.isEnabled)
        hasher.combine(snap.isSelected)

        if let children = snap.children as? [XCUIElementSnapshot] {
            hasher.combine(children.count)
            for child in children {
                hashElement(child, into: &hasher)
            }
        }
    }
}

// MARK: - FNV-1a hash (fast, no allocations)

private struct FNV1aHasher {
    private(set) var value: UInt64 = 14695981039346656037

    mutating func combine(_ int: Int) {
        value ^= UInt64(bitPattern: Int64(int))
        value &*= 1099511628211
    }

    mutating func combine(_ uint: UInt) {
        value ^= UInt64(uint)
        value &*= 1099511628211
    }

    mutating func combine(_ bool: Bool) {
        value ^= bool ? 1 : 0
        value &*= 1099511628211
    }

    mutating func combine(_ string: String) {
        for byte in string.utf8 {
            value ^= UInt64(byte)
            value &*= 1099511628211
        }
    }
}
