import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef, useContext } from 'react';

import { LayoutContext } from '../Layout/LayoutContext';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';

interface PageMainContentProps<T extends keyof ReactHTML = 'main'>
    extends SlottedContainerProps<T> {
    /**
     * Whether the content is scrollable.
     * @default false
     */
    scrollable?: boolean | undefined;
}

const styles = stylex.create({
    content: {
        display: 'flex',
        flexDirection: 'column',
        flexGrow: 1,
        gap: tokens['space-gap-lg'],
        minHeight: 0,
    },
    nonScrollableParent: {},
    scrollable: {
        overflowY: 'auto',
    },
});

const PageMainContent = forwardRef<HTMLElement, PageMainContentProps>(
    function PageMainContent(props, forwardedRef) {
        const { scrollableParent } = useContext(LayoutContext);
        const { scrollable, ...otherProps } = props;

        return (
            <SlottedContainer
                {...otherProps}
                tag="main"
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

export { PageMainContent };
export type { PageMainContentProps };
