@import Foundation;

NS_ASSUME_NONNULL_BEGIN

/// Low-level event synthesis using private XCTest APIs (same approach as WDA).
/// Uses XCPointerEventPath + XCSynthesizedEventRecord to type text directly
/// through the XCTest daemon — no keyboard focus required, returns NSError
/// instead of throwing NSException.
@interface EventSynthesizer : NSObject

/// Types text via the XCTest event synthesizer. Does not require keyboard focus.
/// Returns nil on success, or an NSError on failure.
+ (nullable NSError *)typeText:(NSString *)text typingSpeed:(NSUInteger)speed;

/// Types text with default typing speed (60 chars/sec).
+ (nullable NSError *)typeText:(NSString *)text;

@end

NS_ASSUME_NONNULL_END
