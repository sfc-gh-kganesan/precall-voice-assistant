import * as stylex from '@stylexjs/stylex';
import type { ComponentPropsWithoutRef, ReactHTML } from 'react';
import { forwardRef } from 'react';
import { TabPanel } from 'react-aria-components';

import { useMergedStyles } from '../hooks';

const styles = stylex.create({
    content: {
        overflow: 'auto',
    },
    grow: {
        flexGrow: 1,
    },
});

type TabsContentProps<T extends keyof ReactHTML = 'div'> =
    ComponentPropsWithoutRef<T> & {
        /**
         * The value of the tabs content.
         */
        value: string;
        /**
         * Whether the tabs content should grow to fit tabs root's height.
         */
        grow?: boolean | undefined;
    };

const TabsContent = forwardRef<HTMLDivElement, TabsContentProps>(
    ({ grow, className, style, value, ...props }, forwardedRef) => {
        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(styles.content, grow && styles.grow),
        );

        return (
            <TabPanel
                {...props}
                ref={forwardedRef}
                {...mergedStyles}
                id={value}
            />
        );
    },
);
TabsContent.displayName = 'Tabs.Content';
export type { TabsContentProps };
export { TabsContent };
