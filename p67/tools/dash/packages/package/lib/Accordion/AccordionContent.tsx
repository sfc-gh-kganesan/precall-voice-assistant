import { Slottable } from '@radix-ui/react-slot';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';
import { DisclosurePanel } from 'react-aria-components';

import { useMergedStyles } from '../hooks';
import type { SlottedContainerProps } from '../util/SlottedContainer';

const styles = stylex.create({
    content: {
        height: 'var(--disclosure-panel-height)',
        overflow: 'hidden',
        transitionDuration: '300ms',
        transitionProperty: 'height',
        transitionTimingFunction: 'ease-out',
    },
    inner: {
        padding: tokens['space-vertical-xs'],
    },
});

type AccordionContentProps<T extends keyof ReactHTML = 'div'> = Omit<
    SlottedContainerProps<T>,
    'role'
>;

const AccordionContent = forwardRef<HTMLDivElement, AccordionContentProps>(
    (props, forwardedRef) => {
        const { className, style, children, ...otherProps } = props;
        const stylexProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.content),
        );
        return (
            <DisclosurePanel
                {...otherProps}
                {...stylexProps}
                ref={forwardedRef}
            >
                <div {...stylex.props(styles.inner)}>
                    <Slottable>{children}</Slottable>
                </div>
            </DisclosurePanel>
        );
    },
);

AccordionContent.displayName = 'Accordion.Content';
export type { AccordionContentProps };
export { AccordionContent };
