import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef, useContext } from 'react';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';
import { LayoutContext } from './LayoutContext';

interface LayoutContentProps<T extends keyof ReactHTML = 'div'>
    extends SlottedContainerProps<T> {
    /**
     * Whether the content is scrollable.
     */
    scrollable?: boolean | undefined;
}

const styles = stylex.create({
    content: {
        display: 'flex',
        flexDirection: 'column',
        flexGrow: 1,
        minHeight: 0,
    },
    nonScrollableParent: {},
    scrollable: {
        overflowY: 'auto',
    },
});

const LayoutContent = forwardRef<HTMLElement, LayoutContentProps>(
    (props, forwardedRef) => {
        const { scrollableParent } = useContext(LayoutContext);
        const { scrollable, ...otherProps } = props;

        return (
            <SlottedContainer
                {...otherProps}
                tag="div"
                stylexProps={stylex.props(
                    styles.content,
                    scrollable && !scrollableParent && styles.scrollable,
                    !scrollableParent &&
                        !scrollable &&
                        styles.nonScrollableParent,
                )}
                tabIndex={scrollable ? 0 : undefined}
                ref={forwardedRef}
            />
        );
    },
);

LayoutContent.displayName = 'Layout.Content';

export { LayoutContent };
export type { LayoutContentProps };
