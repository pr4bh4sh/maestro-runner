#import "EventSynthesizer.h"
#import <XCTest/XCTest.h>
#import <stdatomic.h>

// Private XCTest headers — same APIs used by WebDriverAgent
@interface XCPointerEventPath : NSObject
- (instancetype)initForTextInput;
- (void)typeText:(NSString *)text atOffset:(double)offset typingSpeed:(NSUInteger)speed shouldRedact:(BOOL)redact;
@end

@interface XCSynthesizedEventRecord : NSObject
- (instancetype)initWithName:(NSString *)name;
- (void)addPointerEventPath:(XCPointerEventPath *)path;
@end

// XCUIDevice private property for event synthesis
@interface XCUIDevice (EventSynthesis)
@property (readonly) id eventSynthesizer;
@end

// The eventSynthesizer responds to synthesizeEvent:completion:
@protocol XCUIEventSynthesizing <NSObject>
- (void)synthesizeEvent:(XCSynthesizedEventRecord *)event completion:(void (^)(BOOL, NSError *))completion;
@end

@implementation EventSynthesizer

+ (nullable NSError *)typeText:(NSString *)text typingSpeed:(NSUInteger)speed {
    XCSynthesizedEventRecord *record = [[XCSynthesizedEventRecord alloc] initWithName:
        [NSString stringWithFormat:@"Type '%@'", text.length <= 12 ? text : [text substringToIndex:12]]];
    XCPointerEventPath *path = [[XCPointerEventPath alloc] initForTextInput];
    [path typeText:text atOffset:0.0 typingSpeed:speed shouldRedact:NO];
    [record addPointerEventPath:path];

    // Send through XCUIDevice.sharedDevice.eventSynthesizer (same path as WDA).
    // CRITICAL: Must spin the NSRunLoop while waiting — XCTest delivers events
    // through the run loop. Using dispatch_semaphore_wait blocks the run loop
    // and prevents event delivery (events queue but never reach the app).
    __block NSError *synthesizeError = nil;
    __block volatile atomic_bool didFinish = false;

    id synthesizer = [XCUIDevice.sharedDevice eventSynthesizer];
    if (!synthesizer) {
        return [NSError errorWithDomain:@"EventSynthesizer" code:2
                               userInfo:@{NSLocalizedDescriptionKey: @"XCUIDevice.eventSynthesizer is nil"}];
    }

    [(id<XCUIEventSynthesizing>)synthesizer synthesizeEvent:record completion:^(BOOL result, NSError *error) {
        if (!result || error != nil) {
            synthesizeError = error ?: [NSError errorWithDomain:@"EventSynthesizer"
                                                          code:1
                                                      userInfo:@{NSLocalizedDescriptionKey: @"Event synthesis failed"}];
        }
        atomic_fetch_or(&didFinish, true);
    }];

    // Spin the run loop until completion (same pattern as WDA's FBRunLoopSpinner)
    while (!atomic_fetch_and(&didFinish, false)) {
        [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.1]];
    }

    return synthesizeError;
}

+ (nullable NSError *)typeText:(NSString *)text {
    return [self typeText:text typingSpeed:60];
}

@end
