import Foundation
import XCTest

/// Flattened representation of a UI element from the accessibility snapshot.
struct ElementModel {
    let elementType: XCUIElement.ElementType
    let className: String       // e.g. "XCUIElementTypeButton"
    let label: String
    let value: String
    let identifier: String      // accessibilityIdentifier
    let placeholderValue: String
    let isEnabled: Bool
    let isSelected: Bool
    let hasFocus: Bool
    let frame: CGRect           // screen-relative bounds
    let children: [ElementModel]

    /// Whether the element is likely visible (non-zero frame, on screen).
    var isDisplayed: Bool {
        return frame.width > 0 && frame.height > 0
    }

    /// Primary text: label, value, or identifier.
    var text: String {
        if !label.isEmpty { return label }
        if !value.isEmpty { return value }
        return identifier
    }

    /// Whether this element type is typically interactive/clickable.
    var isClickable: Bool {
        switch elementType {
        case .button, .link, .cell, .switch, .toggle,
             .textField, .secureTextField, .searchField,
             .slider, .stepper, .segmentedControl,
             .tab, .tabBar, .picker, .datePicker,
             .menuItem, .menu, .popUpButton:
            return true
        default:
            return false
        }
    }

    /// Convert to JSON-serializable dictionary for the protocol.
    func toDict() -> [String: Any] {
        return [
            "className": className,
            "text": text,
            "label": label,
            "value": value,
            "identifier": identifier,
            "placeholderValue": placeholderValue,
            "enabled": isEnabled,
            "selected": isSelected,
            "focused": hasFocus,
            "displayed": isDisplayed,
            "clickable": isClickable,
            "bounds": [
                "x": Int(frame.origin.x),
                "y": Int(frame.origin.y),
                "width": Int(frame.size.width),
                "height": Int(frame.size.height),
            ],
        ]
    }
}
