import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import type { HTMLAttributes } from 'react';
import { forwardRef } from 'react';

import {
    BadgeActiveBadge,
    BadgeCautionBadge,
    BadgeClockBadge,
    BadgeCriticalBadge,
    BadgeLockBadge,
    BadgePendingBadge,
    BadgePublishBadge,
    BadgeShieldBadge,
    BadgeSuccessBadge,
    BadgeUploadBadge,
    BadgeWaitBadge,
} from './generated/components';
import type { BadgeType as BadgeIllustrationType } from './generated/components/types';
import type { IllustrationSize, IllustrationType } from './types';

interface BadgeIllustrationProps extends HTMLAttributes<SVGSVGElement> {
    /**
     * The variant of the badge illustration.
     */
    variant: IllustrationType;
    /**
     * The size of the badge illustration.
     */
    size: IllustrationSize;
}

const componentMap: { [key in IllustrationType]: BadgeIllustrationType } = {
    shield: BadgeShieldBadge,
    publish: BadgePublishBadge,
    upload: BadgeUploadBadge,
    clock: BadgeClockBadge,
    lock: BadgeLockBadge,
    success: BadgeSuccessBadge,
    caution: BadgeCautionBadge,
    critical: BadgeCriticalBadge,
    active: BadgeActiveBadge,
    pending: BadgePendingBadge,
    wait: BadgeWaitBadge,
};

const sizeMap: { [key in IllustrationSize]: string } = {
    xsmall: tokens['size-2xs'],
    small: tokens['size-sm'],
    medium: tokens['size-lg'],
    large: tokens['size-2xl'],
};

const BadgeIllustration = forwardRef<SVGSVGElement, BadgeIllustrationProps>(
    (props, forwardedRef) => {
        const { variant, size, ...otherProps } = props;
        const IllustrationIcon = componentMap[variant];

        return (
            <IllustrationIcon
                {...otherProps}
                size={sizeMap[size]}
                ref={forwardedRef}
            />
        );
    },
);
BadgeIllustration.displayName = 'BadgeIllustration';
export type { BadgeIllustrationProps };
export { BadgeIllustration };
