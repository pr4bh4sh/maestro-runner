#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

/// Catches Objective-C NSExceptions that Swift cannot handle with do/catch.
@interface ObjCExceptionCatcher : NSObject

/// Executes a block and catches any NSException thrown.
/// Returns nil on success, or the NSException on failure.
+ (nullable NSException *)tryBlock:(void (NS_NOESCAPE ^)(void))block;

@end

NS_ASSUME_NONNULL_END
