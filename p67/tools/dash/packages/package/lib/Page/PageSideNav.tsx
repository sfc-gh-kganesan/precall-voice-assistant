import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';
import { mergeProps } from 'react-aria';

import { useMergedStyles } from '../hooks';
import { useAriaLabel } from '../internal/hooks/useLabel';
import { Layout } from '../Layout';
import type {
    CollapseContext,
    LayoutSidebarProps,
} from '../Layout/LayoutSidebar';
import type { ControlledComponent } from '../util/Controlled';

const styles = stylex.create({
    sideNav: {
        backgroundColor: baltoTheme.reusableBackgroundAdditionalInfo,
        gap: tokens['space-gap-lg'],
        minHeight: tokens['size-2xl'],
        padding: tokens['space-vertical-sm'],
        paddingInlineEnd: 0,
    },
    beforeNav: {
        borderInlineEndColor: baltoTheme.reusableBorderDefault,
        borderInlineEndStyle: 'solid',
        borderInlineEndWidth: 1,
    },
    afterNav: {
        borderInlineStartColor: baltoTheme.reusableBorderDefault,
        borderInlineStartStyle: 'solid',
        borderInlineStartWidth: 1,
    },
});

type PageSideNavProps<T extends keyof ReactHTML = 'nav'> =
    LayoutSidebarProps<T> &
        ControlledComponent<'collapse', boolean, CollapseContext> & {
            /**
             * The position of the side navigation bar.
             * @default "before"
             */
            position?: 'before' | 'after' | undefined;
        };

const PageSideNav = forwardRef<HTMLElement, PageSideNavProps>(
    (props, forwardedRef) => {
        const {
            style,
            className,
            position = 'before',
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledby,
            ...otherProps
        } = props;
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(
                styles.sideNav,
                position === 'before' && styles.beforeNav,
                position === 'after' && styles.afterNav,
            ),
        );
        const { ariaLabelProps } = useAriaLabel({
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledby,
        });
        return (
            <Layout.Sidebar
                {...mergeProps(
                    otherProps,
                    styleProps,
                    ariaLabelProps as LayoutSidebarProps<'nav'>,
                )}
                collapsedWidth={64}
                collapseBreakpoint="sm"
                role="navigation"
                ref={forwardedRef}
            />
        );
    },
);
PageSideNav.displayName = 'Page.SideNav';
export { PageSideNav };
export type { PageSideNavProps };
