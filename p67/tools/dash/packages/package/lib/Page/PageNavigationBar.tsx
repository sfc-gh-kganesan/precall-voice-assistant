import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';

import { useMergedStyles } from '../hooks';
import { Layout } from '../Layout';
import type { LayoutHeaderProps } from '../Layout/LayoutHeader';

interface PageNavigationBarProps<T extends keyof ReactHTML = 'nav'>
    extends LayoutHeaderProps<T> {
    /**
     * The position of the navigation bar.
     * @default "before"
     */
    position?: 'before' | 'after' | undefined;
}

const styles = stylex.create({
    navBar: {
        // vertically centered
        alignItems: 'center',
        backgroundColor: baltoTheme.statusNeutralBackground,
        display: 'flex',
        flexDirection: 'row',
        gap: tokens['space-gap-lg'],
        justifyContent: 'space-between',
        minHeight: tokens['size-2xl'],
        padding: tokens['space-vertical-sm'],
    },
    topNav: {
        borderBlockEndColor: baltoTheme.statusNeutralUi,
        borderBlockEndStyle: 'solid',
        borderBlockEndWidth: 1,
    },
    bottomNav: {
        borderBlockStartColor: baltoTheme.statusNeutralUi,
        borderBlockStartStyle: 'solid',
        borderBlockStartWidth: 1,
    },
});

const PageNavigationBar = forwardRef<HTMLElement, PageNavigationBarProps>(
    (props, forwardedRef) => {
        const { style, className, position = 'before', ...otherProps } = props;

        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(
                styles.navBar,
                position === 'before' && styles.topNav,
                position === 'after' && styles.bottomNav,
            ),
        );
        const Component = position === 'before' ? Layout.Header : Layout.Footer;
        return <Component {...otherProps} {...styleProps} ref={forwardedRef} />;
    },
);
PageNavigationBar.displayName = 'Page.NavigationBar';
export { PageNavigationBar };
export type { PageNavigationBarProps };
