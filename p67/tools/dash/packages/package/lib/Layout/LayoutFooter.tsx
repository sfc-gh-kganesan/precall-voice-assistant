import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';

import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';

interface LayoutFooterProps<T extends keyof ReactHTML = 'footer'>
    extends SlottedContainerProps<T> {
    /**
     * Whether the footer is sticky.
     * @default false
     */
    sticky?: boolean | undefined;
}

const styles = stylex.create({
    default: {
        display: 'flex',
        flexDirection: 'row',
        flexGrow: 0,
        flexShrink: 0,
        justifyContent: 'space-between',
        minHeight: 0,
    },
    sticky: {
        bottom: 0,
        position: 'sticky',
        zIndex: 1,
    },
});

const LayoutFooter = forwardRef<HTMLElement, LayoutFooterProps>(
    (props, forwardedRef) => {
        const { sticky, ...otherProps } = props;

        return (
            <SlottedContainer
                {...otherProps}
                tag="footer"
                stylexProps={stylex.props(
                    styles.default,
                    sticky && styles.sticky,
                )}
                ref={forwardedRef}
            />
        );
    },
);
LayoutFooter.displayName = 'Layout.Footer';
export { LayoutFooter };
export type { LayoutFooterProps };
