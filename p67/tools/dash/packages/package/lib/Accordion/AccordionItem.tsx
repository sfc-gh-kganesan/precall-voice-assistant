import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';
import { Disclosure } from 'react-aria-components';

import { useMergedStyles } from '../hooks';
import type { SlottedContainerProps } from '../util/SlottedContainer';

const styles = stylex.create({
    item: {
        backgroundColor: baltoTheme.surfaceLevel_2Background,
        borderRadius: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 0,
    },
});
interface AccordionItemProps<T extends keyof ReactHTML = 'div'>
    extends SlottedContainerProps<T> {
    /**
     * The value of the accordion item.
     */
    value: string;
}

const AccordionItem = forwardRef<HTMLDivElement, AccordionItemProps>(
    (props, forwardedRef) => {
        const { className, style, value, ...otherProps } = props;
        const stylexProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.item),
        );
        return (
            <Disclosure
                {...otherProps}
                {...stylexProps}
                id={value}
                ref={forwardedRef}
            />
        );
    },
);

AccordionItem.displayName = 'Accordion.Item';
export type { AccordionItemProps };
export { AccordionItem };
