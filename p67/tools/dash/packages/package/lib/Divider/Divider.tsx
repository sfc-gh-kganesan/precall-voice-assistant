import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes } from 'react';
import { forwardRef } from 'react';
import { Separator } from 'react-aria-components';

import { useMergedStyles } from '../hooks';
import { useDividerStyles } from './useDividerStyles';

interface DividerProps extends HTMLAttributes<HTMLHRElement> {
    /**
     * The direction of the divider.
     * @default "horizontal"
     */
    direction?: 'horizontal' | 'vertical' | undefined;
}

const Divider = forwardRef<HTMLHRElement, DividerProps>(
    (props, forwardedRef) => {
        const {
            className,
            style,
            direction = 'horizontal',
            ...otherProps
        } = props;
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(useDividerStyles({ direction })),
        );

        return (
            <Separator
                {...styleProps}
                {...otherProps}
                ref={forwardedRef}
                orientation={direction}
            />
        );
    },
);
Divider.displayName = 'Divider';
export type { DividerProps };
export { Divider };
