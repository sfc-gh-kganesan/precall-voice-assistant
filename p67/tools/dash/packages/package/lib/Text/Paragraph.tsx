import { IconContextProvider } from '@snowflake/stellar-icons';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef, useContext, useMemo } from 'react';
import type { Size } from '../types';
import { SizeContext } from '../util/context';
import { devWarning } from '../util/dev-warning';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';
import {
    ParagraphContext,
    type ParagraphContextValue,
} from './internal/ParagraphContext';
import { useParagraphStyles } from './internal/useParagraphStyles';
import type { TextVariant } from './types';

/**
 * Props interface for the Paragraph component.
 *
 * @template T - HTML element type, defaults to "p".
 *  Do Not specify unless used with asChild and you are unable to add props directly to the child.
 * @extends {SlottedContainerProps<T>}
 */
interface ParagraphProps<T extends keyof ReactHTML = 'p'>
    extends SlottedContainerProps<T> {
    /** The visual style variant of the text. primary variant used by default */
    variant?: TextVariant | undefined;

    /** Whether the text should be displayed in bold. Defaults to false */
    bold?: boolean | undefined;

    /** The size of the text. Can be either "small" or "regular". Defaults to "regular" */
    size?: Extract<Size, 'small' | 'regular'> | undefined;

    /** Whether the text should be displayed in all capitals. Defaults to false */
    caps?: boolean | undefined;

    /** Maximum width of the paragraph in em units. Defaults to and capped at 70em */
    maxWidth?: number | undefined;
}

const styles = stylex.create({
    paragraph: {
        margin: 0,
        padding: 0,
        whiteSpaceCollapse: 'collapse',
    },
    limitWidth: (limit: number) => ({
        maxWidth: `${limit}em`,
    }),
});

/**
 * A component for rendering multi-line text paragraphs using Balto Typography options.
 *
 * @remarks
 * Nested paragraphs are not supported and will trigger a warning.
 *
 * @example
 * ```tsx
 * <Paragraph>
 *   This is a sample paragraph
 * </Paragraph>
 * ```
 *
 *  @example
 * ```tsx
 * <Paragraph size="small" variant="secondary">
 *   This is a sample paragraph
 * </Paragraph>
 * ```
 *
 * @interface ParagraphProps
 * @property {TextVariant} [variant="primary"] - The visual style variant of the paragraph
 * @property {boolean} [bold=false] - Whether to display the text in bold
 * @property {"small" | "regular"} [size="regular"] - The text size of the paragraph
 * @property {boolean} [caps=false] - Whether to display the text in all capitals
 * @property {number} [maxWidth] - Maximum width of the paragraph in em units (capped at 70em)
 *
 * @returns A styled paragraph element that supports icons and custom styling
 *
 * @throws {Warning} When attempting to nest Paragraph components
 */
const Paragraph = forwardRef<HTMLParagraphElement, ParagraphProps>(
    (props, forwardedRef) => {
        const contextSize = useContext(SizeContext);
        const {
            size = contextSize ?? 'regular',
            caps = false,
            variant = 'primary',
            bold = false,
            maxWidth,
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
        const safeMaxWidth = useMemo(() => {
            if (maxWidth) {
                if (maxWidth && maxWidth > 0 && maxWidth < 70) {
                    return maxWidth;
                }
                devWarning(
                    `Paragraph maxWidth is capped at 70em, received ${maxWidth}em. Resetting to 70 EM`,
                );
            }
            return 70;
        }, [maxWidth]);

        return (
            <IconContextProvider>
                <ParagraphContext.Provider value={paragraphContext}>
                    <SlottedContainer
                        {...otherProps}
                        tag={'p'}
                        stylexProps={stylex.props(
                            styles.paragraph,
                            styles.limitWidth(safeMaxWidth), // 70em is the max width of the container
                            ...paragraphStyles,
                        )}
                        ref={forwardedRef}
                    />
                </ParagraphContext.Provider>
            </IconContextProvider>
        );
    },
);

Paragraph.displayName = 'Paragraph';
export type { ParagraphProps };
export { Paragraph };
