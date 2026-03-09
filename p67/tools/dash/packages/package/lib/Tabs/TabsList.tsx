import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';
import { mergeProps } from 'react-aria';
import { TabList as TabListPrimitive } from 'react-aria-components';

import { useMergedStyles } from '../hooks';
import { useAriaLabel } from '../internal/hooks/useLabel';
import type { SlottedContainerProps } from '../util/SlottedContainer';

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface TabsListBaseProps<T extends keyof ReactHTML = 'footer'>
    extends SlottedContainerProps<T> {}

interface TabsListAriaLabelProps<T extends keyof ReactHTML = 'footer'>
    extends TabsListBaseProps<T> {
    /**
     * The aria label of the tabs list.
     */
    'aria-label': string;
}

interface TabsListAriaLabelledbyProps<T extends keyof ReactHTML = 'footer'>
    extends TabsListBaseProps<T> {
    /**
     * The aria labelledby of the tabs list.
     */
    'aria-labelledby': string;
}

type TabsListProps<T extends keyof ReactHTML = 'footer'> =
    | TabsListAriaLabelProps<T>
    | TabsListAriaLabelledbyProps<T>;

const styles = stylex.create({
    list: {
        display: 'flex',
        gap: tokens['space-gap-2xl'],
        height: tokens['size-lg'],
        overflowX: 'auto',
        position: 'relative',

        '::before': {
            borderBottomColor: baltoTheme.reusableBorderDefault,
            borderBottomStyle: 'solid',
            borderBottomWidth: 1,
            content: "''",
            inset: 0,
            position: 'absolute',
        },
    },
});

const TabsList = forwardRef<HTMLDivElement, TabsListProps>(
    (props, forwardedRef) => {
        const {
            className,
            style,
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledby,
            ...otherProps
        } = props;
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.list),
        );
        const { ariaLabelProps } = useAriaLabel({
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledby,
        });

        return (
            <TabListPrimitive
                {...mergeProps(styleProps, ariaLabelProps, otherProps)}
                ref={forwardedRef}
            />
        );
    },
);

TabsList.displayName = 'Tabs.List';

export type { TabsListProps };
export { TabsList };
