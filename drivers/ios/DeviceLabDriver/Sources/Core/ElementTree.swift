import Foundation
import XCTest

/// Converts XCUIElementSnapshot tree into flat [ElementModel] and provides search.
enum ElementTree {

    // MARK: - Build from snapshot

    /// Flatten an XCUIElementSnapshot into an array of ElementModel.
    static func flatten(_ snapshot: XCUIElementSnapshot) -> [ElementModel] {
        var result: [ElementModel] = []
        buildElement(from: snapshot, into: &result)
        return result
    }

    private static func buildElement(from snap: XCUIElementSnapshot, into result: inout [ElementModel]) {
        let children = (snap.children as? [XCUIElementSnapshot]) ?? []
        var childModels: [ElementModel] = []
        for child in children {
            buildElement(from: child, into: &result)
            // We only store direct children for XML serialization
            childModels.append(makeElement(from: child, children: []))
        }
        let elem = makeElement(from: snap, children: childModels)
        result.append(elem)
    }

    private static func makeElement(from snap: XCUIElementSnapshot, children: [ElementModel]) -> ElementModel {
        return ElementModel(
            elementType: snap.elementType,
            className: elementTypeName(snap.elementType),
            label: snap.label ?? "",
            value: (snap.value as? String) ?? "",
            identifier: snap.identifier,
            placeholderValue: snap.placeholderValue ?? "",
            isEnabled: snap.isEnabled,
            isSelected: snap.isSelected,
            hasFocus: snap.hasFocus,
            frame: snap.frame,
            children: children
        )
    }

    // MARK: - Search

    /// Find elements matching text (case-insensitive contains).
    static func findByText(_ elements: [ElementModel], text: String) -> [ElementModel] {
        let lower = text.lowercased()
        return elements.filter { elem in
            elem.label.lowercased().contains(lower) ||
            elem.value.lowercased().contains(lower) ||
            elem.identifier.lowercased().contains(lower) ||
            elem.placeholderValue.lowercased().contains(lower)
        }
    }

    /// Find elements matching accessibility identifier.
    static func findByID(_ elements: [ElementModel], id: String) -> [ElementModel] {
        let lower = id.lowercased()
        return elements.filter { $0.identifier.lowercased().contains(lower) }
    }

    /// Find elements matching element type name.
    static func findByType(_ elements: [ElementModel], type: String) -> [ElementModel] {
        let lower = type.lowercased()
        return elements.filter { $0.className.lowercased().contains(lower) }
    }

    /// Filter to only visible elements (non-zero frame).
    static func filterVisible(_ elements: [ElementModel]) -> [ElementModel] {
        return elements.filter { $0.isDisplayed }
    }

    /// Sort clickable/interactive elements first.
    static func sortClickableFirst(_ elements: [ElementModel]) -> [ElementModel] {
        return elements.sorted { a, b in
            if a.isClickable && !b.isClickable { return true }
            if !a.isClickable && b.isClickable { return false }
            return false // preserve order
        }
    }

    /// Find the best element for tap: visible, prefer clickable, prefer exact text match.
    static func findForTap(_ elements: [ElementModel], text: String) -> ElementModel? {
        let lower = text.lowercased()
        let matches = elements.filter { elem in
            guard elem.isDisplayed else { return false }
            return elem.label.lowercased().contains(lower) ||
                   elem.value.lowercased().contains(lower) ||
                   elem.identifier.lowercased().contains(lower) ||
                   elem.placeholderValue.lowercased().contains(lower)
        }

        if matches.isEmpty { return nil }

        // Prefer exact match
        let exactMatches = matches.filter { elem in
            elem.label.lowercased() == lower ||
            elem.value.lowercased() == lower ||
            elem.identifier.lowercased() == lower
        }

        let pool = exactMatches.isEmpty ? matches : exactMatches

        // Prefer clickable
        if let clickable = pool.first(where: { $0.isClickable }) {
            return clickable
        }

        return pool.first
    }

    // MARK: - XML Serialization (WDA-compatible format)

    /// Serialize snapshot to XML matching WDA's page source format.
    static func snapshotToXML(_ snapshot: XCUIElementSnapshot, screenSize: CGSize) -> String {
        var xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        appendElementXML(snapshot, to: &xml, indent: 0, screenSize: screenSize)
        return xml
    }

    private static func appendElementXML(_ snap: XCUIElementSnapshot, to xml: inout String, indent: Int, screenSize: CGSize) {
        let typeName = elementTypeName(snap.elementType)
        let pad = String(repeating: "  ", count: indent)

        let label = escapeXML(snap.label ?? "")
        let value = escapeXML((snap.value as? String) ?? "")
        let name = escapeXML(snap.identifier)
        let placeholder = escapeXML(snap.placeholderValue ?? "")

        let frame = snap.frame
        let visible = frame.width > 0 && frame.height > 0 &&
                      frame.origin.x < screenSize.width && frame.origin.y < screenSize.height

        let children = (snap.children as? [XCUIElementSnapshot]) ?? []

        if children.isEmpty {
            xml += "\(pad)<\(typeName)"
            xml += " type=\"\(typeName)\""
            xml += " enabled=\"\(snap.isEnabled)\""
            xml += " visible=\"\(visible)\""
            if !name.isEmpty { xml += " name=\"\(name)\"" }
            if !label.isEmpty { xml += " label=\"\(label)\"" }
            if !value.isEmpty { xml += " value=\"\(value)\"" }
            if !placeholder.isEmpty { xml += " placeholderValue=\"\(placeholder)\"" }
            xml += " x=\"\(Int(frame.origin.x))\""
            xml += " y=\"\(Int(frame.origin.y))\""
            xml += " width=\"\(Int(frame.size.width))\""
            xml += " height=\"\(Int(frame.size.height))\""
            xml += " />\n"
        } else {
            xml += "\(pad)<\(typeName)"
            xml += " type=\"\(typeName)\""
            xml += " enabled=\"\(snap.isEnabled)\""
            xml += " visible=\"\(visible)\""
            if !name.isEmpty { xml += " name=\"\(name)\"" }
            if !label.isEmpty { xml += " label=\"\(label)\"" }
            if !value.isEmpty { xml += " value=\"\(value)\"" }
            if !placeholder.isEmpty { xml += " placeholderValue=\"\(placeholder)\"" }
            xml += " x=\"\(Int(frame.origin.x))\""
            xml += " y=\"\(Int(frame.origin.y))\""
            xml += " width=\"\(Int(frame.size.width))\""
            xml += " height=\"\(Int(frame.size.height))\""
            xml += ">\n"
            for child in children {
                appendElementXML(child, to: &xml, indent: indent + 1, screenSize: screenSize)
            }
            xml += "\(pad)</\(typeName)>\n"
        }
    }

    private static func escapeXML(_ s: String) -> String {
        return s.replacingOccurrences(of: "&", with: "&amp;")
                .replacingOccurrences(of: "<", with: "&lt;")
                .replacingOccurrences(of: ">", with: "&gt;")
                .replacingOccurrences(of: "\"", with: "&quot;")
                .replacingOccurrences(of: "'", with: "&apos;")
    }

    // MARK: - Element type names

    static func elementTypeName(_ type: XCUIElement.ElementType) -> String {
        switch type {
        case .any:                return "XCUIElementTypeAny"
        case .other:              return "XCUIElementTypeOther"
        case .application:        return "XCUIElementTypeApplication"
        case .group:              return "XCUIElementTypeGroup"
        case .window:             return "XCUIElementTypeWindow"
        case .sheet:              return "XCUIElementTypeSheet"
        case .drawer:             return "XCUIElementTypeDrawer"
        case .alert:              return "XCUIElementTypeAlert"
        case .dialog:             return "XCUIElementTypeDialog"
        case .button:             return "XCUIElementTypeButton"
        case .radioButton:        return "XCUIElementTypeRadioButton"
        case .radioGroup:         return "XCUIElementTypeRadioGroup"
        case .checkBox:           return "XCUIElementTypeCheckBox"
        case .disclosureTriangle: return "XCUIElementTypeDisclosureTriangle"
        case .popUpButton:        return "XCUIElementTypePopUpButton"
        case .comboBox:           return "XCUIElementTypeComboBox"
        case .menuButton:         return "XCUIElementTypeMenuButton"
        case .toolbarButton:      return "XCUIElementTypeToolbarButton"
        case .popover:            return "XCUIElementTypePopover"
        case .keyboard:           return "XCUIElementTypeKeyboard"
        case .key:                return "XCUIElementTypeKey"
        case .navigationBar:      return "XCUIElementTypeNavigationBar"
        case .tabBar:             return "XCUIElementTypeTabBar"
        case .tabGroup:           return "XCUIElementTypeTabGroup"
        case .toolbar:            return "XCUIElementTypeToolbar"
        case .statusBar:          return "XCUIElementTypeStatusBar"
        case .table:              return "XCUIElementTypeTable"
        case .tableRow:           return "XCUIElementTypeTableRow"
        case .tableColumn:        return "XCUIElementTypeTableColumn"
        case .outline:            return "XCUIElementTypeOutline"
        case .outlineRow:         return "XCUIElementTypeOutlineRow"
        case .browser:            return "XCUIElementTypeBrowser"
        case .collectionView:     return "XCUIElementTypeCollectionView"
        case .slider:             return "XCUIElementTypeSlider"
        case .pageIndicator:      return "XCUIElementTypePageIndicator"
        case .progressIndicator:  return "XCUIElementTypeProgressIndicator"
        case .activityIndicator:  return "XCUIElementTypeActivityIndicator"
        case .segmentedControl:   return "XCUIElementTypeSegmentedControl"
        case .picker:             return "XCUIElementTypePicker"
        case .pickerWheel:        return "XCUIElementTypePickerWheel"
        case .switch:             return "XCUIElementTypeSwitch"
        case .toggle:             return "XCUIElementTypeToggle"
        case .link:               return "XCUIElementTypeLink"
        case .image:              return "XCUIElementTypeImage"
        case .icon:               return "XCUIElementTypeIcon"
        case .searchField:        return "XCUIElementTypeSearchField"
        case .scrollView:         return "XCUIElementTypeScrollView"
        case .scrollBar:          return "XCUIElementTypeScrollBar"
        case .staticText:         return "XCUIElementTypeStaticText"
        case .textField:          return "XCUIElementTypeTextField"
        case .secureTextField:    return "XCUIElementTypeSecureTextField"
        case .datePicker:         return "XCUIElementTypeDatePicker"
        case .textView:           return "XCUIElementTypeTextView"
        case .menu:               return "XCUIElementTypeMenu"
        case .menuItem:           return "XCUIElementTypeMenuItem"
        case .menuBar:            return "XCUIElementTypeMenuBar"
        case .menuBarItem:        return "XCUIElementTypeMenuBarItem"
        case .map:                return "XCUIElementTypeMap"
        case .webView:            return "XCUIElementTypeWebView"
        case .incrementArrow:     return "XCUIElementTypeIncrementArrow"
        case .decrementArrow:     return "XCUIElementTypeDecrementArrow"
        case .timeline:           return "XCUIElementTypeTimeline"
        case .ratingIndicator:    return "XCUIElementTypeRatingIndicator"
        case .valueIndicator:     return "XCUIElementTypeValueIndicator"
        case .splitGroup:         return "XCUIElementTypeSplitGroup"
        case .splitter:           return "XCUIElementTypeSplitter"
        case .relevanceIndicator: return "XCUIElementTypeRelevanceIndicator"
        case .colorWell:          return "XCUIElementTypeColorWell"
        case .helpTag:            return "XCUIElementTypeHelpTag"
        case .matte:              return "XCUIElementTypeMatte"
        case .dockItem:           return "XCUIElementTypeDockItem"
        case .ruler:              return "XCUIElementTypeRuler"
        case .rulerMarker:        return "XCUIElementTypeRulerMarker"
        case .grid:               return "XCUIElementTypeGrid"
        case .levelIndicator:     return "XCUIElementTypeLevelIndicator"
        case .cell:               return "XCUIElementTypeCell"
        case .layoutArea:         return "XCUIElementTypeLayoutArea"
        case .layoutItem:         return "XCUIElementTypeLayoutItem"
        case .handle:             return "XCUIElementTypeHandle"
        case .stepper:            return "XCUIElementTypeStepper"
        case .tab:                return "XCUIElementTypeTab"
        case .touchBar:           return "XCUIElementTypeTouchBar"
        case .statusItem:         return "XCUIElementTypeStatusItem"
        @unknown default:         return "XCUIElementTypeOther"
        }
    }
}
