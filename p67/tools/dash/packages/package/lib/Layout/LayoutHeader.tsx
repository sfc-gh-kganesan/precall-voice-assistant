import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';

import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';

interface LayoutHeaderProps<T extends keyof ReactHTML = 'header'>
    extends SlottedContainerProps<T> {
    /**
     * Whether the header is sticky.
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
        position: 'sticky',
        top: 0,
        zIndex: 1,
    },
});

const LayoutHeader = forwardRef<HTMLElement, LayoutHeaderProps>(
    (props, forwardedRef) => {
        const { sticky, ...otherProps } = props;

        return (
            <SlottedContainer
                {...otherProps}
                tag="header"
                stylexProps={stylex.props(
                    styles.default,
                    sticky && styles.sticky,
                )}
                ref={forwardedRef}
            />
        );
    },
);
LayoutHeader.displayName = 'Layout.Header';
export { LayoutHeader };
export type { LayoutHeaderProps };
