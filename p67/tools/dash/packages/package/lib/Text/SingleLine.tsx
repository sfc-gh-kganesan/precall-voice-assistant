import { IconContextProvider } from '@snowflake/stellar-icons';
import * as stylex from '@stylexjs/stylex';
import { forwardRef, useContext, useMemo } from 'react';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { OverflowTooltip, SizeContext } from '../main';
import { TooltipContext } from '../Tooltip/TooltipContext';
import { devWarning } from '../util/dev-warning';
import { SlottedContainer } from '../util/SlottedContainer';
import {
    ParagraphContext,
    type ParagraphContextValue,
} from './internal/ParagraphContext';
import { useParagraphStyles } from './internal/useParagraphStyles';
import type { ParagraphProps } from './Paragraph';

const styles = stylex.create({
    singleLine: {
        cursor: 'text',
        display: {
            ':is(*)': 'block',
        },
        margin: 0,
        overflow: 'hidden',
        padding: 0,
        textOverflow: 'ellipsis',
        textWrap: 'nowrap',
        whiteSpace: 'nowrap',
        whiteSpaceCollapse: 'collapse',
    },
});

const SingleLine = forwardRef<HTMLParagraphElement, ParagraphProps>(
    (props, forwardedRef) => {
        const contextSize = useContext(SizeContext);
        const {
            size = contextSize ?? 'regular',
            caps = false,
            variant = 'primary',
            bold = false,
            ...otherProps
        } = props;
        const parentParagraphContext = useContext(ParagraphContext);
        if (parentParagraphContext !== null) {
            devWarning('Nested Paragraphs are not supported.');
        }
        const paragraphContext = useMemo(
            (): ParagraphContextValue => ({
                bold,
                small: size === 'small',
                variant,
                caps,
            }),
            [bold, caps, size, variant],
        );
        const paragraphStyles = useParagraphStyles(paragraphContext);

        const textStyles = useTypeRamp(
            size === 'small'
                ? caps
                    ? 'allCapsSmall'
                    : bold
                      ? 'smallSingleLineBold'
                      : 'smallSingleLine'
                : caps
                  ? 'allCaps'
                  : bold
                    ? 'boldSingleLine'
                    : 'regularSingleLine',
        );
        const tooltipContext = useContext(TooltipContext);
        const content = (
            <SlottedContainer
                {...otherProps}
                tag={'p'}
                stylexProps={stylex.props(
                    styles.singleLine,
                    paragraphStyles,
                    textStyles,
                )}
                ref={forwardedRef}
            />
        );

        return (
            <IconContextProvider>
                <ParagraphContext.Provider value={paragraphContext}>
                    {tooltipContext ? (
                        content
                    ) : (
                        <OverflowTooltip.Root asChild>
                            {content}
                        </OverflowTooltip.Root>
                    )}
                </ParagraphContext.Provider>
            </IconContextProvider>
        );
    },
);

SingleLine.displayName = 'SingleLine';
export type { ParagraphProps };
export { SingleLine };
