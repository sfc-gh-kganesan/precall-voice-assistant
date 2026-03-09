import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { IconContextProvider } from '@snowflake/stellar-icons';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef, useContext, useMemo } from 'react';
import type { Size } from '../types';
import { SizeContext } from '../util/context';
import { devWarning } from '../util/dev-warning';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';
import type { ParagraphContextValue } from './internal/ParagraphContext';
import { ParagraphContext } from './internal/ParagraphContext';
import { useParagraphStyles } from './internal/useParagraphStyles';
import type { TextVariant } from './types';

interface SpanProps<T extends keyof ReactHTML = 'span'>
    extends SlottedContainerProps<T> {
    /**
     * The variant of the span.
     */
    variant?: TextVariant | undefined;
    /**
     * Whether the span is bold.
     * @default false
     */
    bold?: boolean | undefined;
    /**
     * The size of the span.
     * @default "regular"
     */
    size?: Extract<Size, 'small' | 'regular'> | undefined;
    /**
     * Whether the span should be truncated.
     * @default false
     */
    truncate?: boolean | undefined;
}

const styles = stylex.create({
    span: {
        margin: 0,
        padding: 0,
    },
    primary: {
        color: baltoTheme.reusableTextPrimary,
    },
    secondary: {
        color: baltoTheme.reusableTextSecondary,
    },
    truncate: {
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
    },
});

const Span = forwardRef<HTMLSpanElement, SpanProps>((props, forwardedRef) => {
    const contextSize = useContext(SizeContext);
    const {
        bold,
        size = contextSize ?? 'regular',
        variant,
        children,
        truncate,
        ...otherProps
    } = props;
    const parentParagraphContext = useContext(ParagraphContext);
    if (parentParagraphContext === null) {
        devWarning('Span without a Paragraph around it is not supported.');
    }
    const spanContext = useMemo(
        (): ParagraphContextValue => ({
            bold: bold ?? parentParagraphContext?.bold ?? false,
            small: size === 'small' || (parentParagraphContext?.small ?? false),
            variant: variant ?? parentParagraphContext?.variant ?? 'primary',
            caps: parentParagraphContext?.caps ?? false,
        }),
        [bold, parentParagraphContext, size, variant],
    );
    const paragraphStyles = useParagraphStyles(spanContext);

    return (
        <IconContextProvider>
            <SlottedContainer
                {...otherProps}
                tag={'span'}
                stylexProps={stylex.props(
                    styles.span,
                    ...paragraphStyles,
                    truncate && styles.truncate,
                )}
                ref={forwardedRef}
            >
                {children}
            </SlottedContainer>
        </IconContextProvider>
    );
});

Span.displayName = 'Span';
export type { SpanProps };
export { Span };
