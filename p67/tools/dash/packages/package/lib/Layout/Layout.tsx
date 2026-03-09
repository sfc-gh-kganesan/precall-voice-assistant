import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef, useContext } from 'react';
import { HeadingContext } from '../Text/internal/HeadingContext';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';
import { LayoutContent } from './LayoutContent';
import { LayoutContext, useLayoutContextValue } from './LayoutContext';
import { LayoutFooter } from './LayoutFooter';
import { LayoutHeader } from './LayoutHeader';
import { LayoutSidebar } from './LayoutSidebar';

interface LayoutProps<T extends keyof ReactHTML = 'section'>
    extends SlottedContainerProps<T> {
    /**
     * Whether the layout is scrollable.
     * @default false
     */
    scrollable?: boolean | undefined;
    /** Whether the layout has a sidebar. If not provided this is calculated during render and might cause layout shift. */
    hasSidebar?: boolean | undefined;
}

const styles = stylex.create({
    layout: {
        display: 'flex',
        flex: 'auto',
        flexDirection: 'column',
        minHeight: 0,
    },
    withSidebar: {
        flexDirection: 'row',
    },
    scrollable: {
        display: 'block',
        overflowY: 'auto',
        position: 'relative',
    },
});

const LayoutComponent = forwardRef<HTMLDivElement, LayoutProps>(
    (props, forwardedRef) => {
        const { scrollable, hasSidebar: hasSidebarProp, ...otherProps } = props;
        const { scrollableParent } = useContext(LayoutContext);

        const contextValue = useLayoutContextValue(
            (scrollableParent || scrollable) ?? false,
        );
        const headingContext = useContext(HeadingContext);
        const hasSidebar = hasSidebarProp ?? contextValue.hasSidebar;

        return (
            <LayoutContext.Provider value={contextValue}>
                <SlottedContainer
                    {...otherProps}
                    tag={
                        headingContext && headingContext.level > 1
                            ? 'section'
                            : 'div'
                    }
                    stylexProps={stylex.props(
                        styles.layout,
                        hasSidebar && styles.withSidebar,
                        scrollable && styles.scrollable,
                    )}
                    tabIndex={scrollable ? 0 : undefined}
                    ref={forwardedRef}
                />
            </LayoutContext.Provider>
        );
    },
);

LayoutComponent.displayName = 'Layout.Root';

export {
    LayoutComponent as Root,
    LayoutContent as Content,
    LayoutFooter as Footer,
    LayoutHeader as Header,
    LayoutSidebar as Sidebar,
};
export type { LayoutContentProps } from './LayoutContent';
export type { LayoutFooterProps } from './LayoutFooter';
export type { LayoutHeaderProps } from './LayoutHeader';
export type { LayoutSidebarProps } from './LayoutSidebar';
export type { LayoutProps };
