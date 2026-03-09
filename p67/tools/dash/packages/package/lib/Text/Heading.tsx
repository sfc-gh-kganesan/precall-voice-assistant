import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { IconContextProvider } from '@snowflake/stellar-icons';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';
import { useHeadingTag } from './internal/useHeadingTag';

type HeadingSize = 'pageHeader' | 'subHeader';

interface HeadingProps<T extends keyof ReactHTML = 'h3'>
    extends SlottedContainerProps<T> {
    /**
     * The size of the heading.
     * @default "subHeader"
     */
    size: HeadingSize;
}

const styles = stylex.create({
    heading: {
        color: baltoTheme.reusableTextHeader,
        margin: 0,
        padding: 0,
        textWrap: 'balance',
    },
});

const Heading = forwardRef<HTMLHeadingElement, HeadingProps>(
    (props, forwardedRef) => {
        const { size, ...otherProps } = props;

        const textStyles = useTypeRamp(
            size === 'pageHeader' ? 'pageHeader' : 'subHeader',
        );
        const { tag } = useHeadingTag();
        return (
            <IconContextProvider>
                <SlottedContainer
                    {...otherProps}
                    tag={tag}
                    stylexProps={stylex.props(textStyles, styles.heading)}
                    ref={forwardedRef}
                />
            </IconContextProvider>
        );
    },
);

Heading.displayName = 'Heading';
export type { HeadingProps, HeadingSize };
export { Heading };
