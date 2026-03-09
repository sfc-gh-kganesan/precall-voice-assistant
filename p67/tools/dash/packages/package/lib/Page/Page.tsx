import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';
import { useMergedStyles } from '../hooks';
import { Layout } from '../Layout';
import type { PageVariant } from '../Layout/PageContext';
import { PageContext } from '../Layout/PageContext';
import {
    HeadingContext,
    useCreateHeadingContext,
} from '../Text/internal/HeadingContext';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { PageMainContent } from './PageMainContent';
import { PageNavigationBar } from './PageNavigationBar';
import { PageSideNav } from './PageSideNav';

interface PageProps<T extends keyof ReactHTML = 'div'>
    extends SlottedContainerProps<T> {
    /**
     * The top navigation bar of the page.
     */
    topNav?: React.ReactNode | undefined;
    /**
     * The bottom navigation bar of the page.
     */
    bottomNav?: React.ReactNode | undefined;
    /**
     * The sidebar of the page.
     */
    sidebar?: React.ReactNode | undefined;
    /**
     * Whether the content is scrollable.
     * @default false
     */
    scrollContent?: boolean | undefined;
    /**
     * The variant of the grid.
     */
    variant?: PageVariant | undefined;
    /**
     * The height of the page.
     */
    height?: string | undefined;
}

const styles = stylex.create({
    base: {
        backgroundColor: baltoTheme.surfaceLevel_1Background,
    },
});

const PageComponent = forwardRef<HTMLDivElement, PageProps>(
    (props, forwardedRef) => {
        const {
            topNav,
            bottomNav,
            className,
            style,
            sidebar,
            scrollContent,
            variant,
            children,
            ...otherProps
        } = props;

        const headingContext = useCreateHeadingContext();
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.base),
        );

        if (!topNav && !bottomNav && !sidebar) {
            return (
                <PageContext.Provider value={{ variant }}>
                    <HeadingContext.Provider value={headingContext}>
                        <PageMainContent
                            {...otherProps}
                            {...styleProps}
                            ref={forwardedRef}
                        >
                            {children}
                        </PageMainContent>
                    </HeadingContext.Provider>
                </PageContext.Provider>
            );
        }
        if (!sidebar) {
            return (
                <PageContext.Provider value={{ variant }}>
                    <HeadingContext.Provider value={headingContext}>
                        <Layout.Root
                            {...otherProps}
                            {...styleProps}
                            scrollable={!scrollContent}
                            ref={forwardedRef}
                        >
                            {topNav}
                            <PageMainContent scrollable={scrollContent}>
                                {children}
                            </PageMainContent>
                            {bottomNav}
                        </Layout.Root>
                    </HeadingContext.Provider>
                </PageContext.Provider>
            );
        }

        return (
            <PageContext.Provider value={{ variant }}>
                <HeadingContext.Provider value={headingContext}>
                    <Layout.Root
                        scrollable={!scrollContent}
                        {...otherProps}
                        {...styleProps}
                        ref={forwardedRef}
                    >
                        {topNav}
                        <Layout.Root hasSidebar>
                            {sidebar}
                            <PageMainContent scrollable={scrollContent}>
                                {children}
                            </PageMainContent>
                        </Layout.Root>
                    </Layout.Root>
                </HeadingContext.Provider>
            </PageContext.Provider>
        );
    },
);

PageComponent.displayName = 'Page.Root';

export {
    PageComponent as Root,
    PageNavigationBar as NavigationBar,
    PageSideNav as SideNav,
};
export type { PageNavigationBarProps } from './PageNavigationBar';
export type { PageSideNavProps } from './PageSideNav';
export type { PageProps };
