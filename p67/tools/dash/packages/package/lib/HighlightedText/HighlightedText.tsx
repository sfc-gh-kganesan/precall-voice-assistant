import { useId, useLayoutEffect } from '@react-aria/utils';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes } from 'react';
import { forwardRef, useCallback, useEffect, useRef } from 'react';
import { useMergedStyles } from '../hooks';
import { HighlightContext } from './context';
import { useHighlightMatch } from './useHighlightMatch';

const HIGHLIGHT_ID = 'highlighted-text';

const styles = stylex.create({
    highlighted: {
        backgroundColor: {
            '::highlight(highlighted-text)':
                baltoTheme.reusableSelectedBackground,
        },
        color: {
            '::highlight(highlighted-text)': baltoTheme.reusableSelectedText,
        },
    },
});

interface HighlightedTextProps
    extends Omit<HTMLAttributes<HTMLSpanElement>, 'children'> {
    /**
     * The children of the highlighted text.
     */
    children: string;
}

const HighlightedText = forwardRef<HTMLSpanElement, HighlightedTextProps>(
    function HighlightedText({ className, style, ...props }, ref) {
        const genId = useId();
        const id = props.id || genId;

        useHighlightMatch({ labelId: id, label: props.children });

        return (
            <span
                ref={ref}
                id={id}
                {...useMergedStyles(
                    className,
                    style,
                    stylex.props(styles.highlighted),
                )}
                {...props}
            />
        );
    },
);

HighlightedText.displayName = 'HighlightedText';

/**
 * The function that renders the highlights.
 */
function renderHighlights(
    id: string,
    allRanges: Map<string, [number, number][]>,
) {
    return requestAnimationFrame(() => {
        if (typeof CSS.highlights === 'undefined') {
            return;
        }

        const rangeObjects: Range[] = [];

        for (const [labelId, ranges] of allRanges.entries()) {
            const el =
                // In some cases the label is far away from the root element
                document.querySelector(
                    `[data-highlight-id='${labelId}'] [data-label]`,
                ) ||
                document.querySelector(`[data-highlight-id='${labelId}']`) ||
                document.querySelector(`[id='${labelId}']`);

            if (!el || !el.firstChild) {
                continue;
            }

            for (const range of ranges) {
                try {
                    const rangeObject = new Range();
                    rangeObject.setStart(el.firstChild, range[0]);
                    rangeObject.setEnd(el.firstChild, range[1]);
                    rangeObjects.push(rangeObject);
                } catch (error) {
                    console.error('Error rendering highlights', error);
                    console.info('All ranges', el, range);
                }
            }
        }

        if (rangeObjects.length === 0) {
            CSS.highlights.delete(id);
            return;
        }

        const highlight = new Highlight(...rangeObjects);

        CSS.highlights.set(id, highlight);
    });
}

/**
 * The provider that renders the highlights.
 */
function HighlightedTextProvider({
    wrapperRef,
    children,
    inputValue,
}: {
    /**
     * The ref of the wrapper element.
     */
    wrapperRef?: React.RefObject<HTMLElement> | HTMLElement | null | undefined;
    /**
     * The children of the highlighted text provider.
     */
    children: React.ReactNode;
    /**
     * The value of the input.
     */
    inputValue: string;
}) {
    const rangesRef = useRef(new Map<string, [number, number][]>());

    // Reset state when input changes
    useLayoutEffect(() => {
        rangesRef.current = new Map<string, [number, number][]>();
    }, [inputValue]);

    const animationFrameId = useRef<number | null>(null);
    const onRenderHighlights = useCallback(() => {
        if (animationFrameId.current) {
            cancelAnimationFrame(animationFrameId.current);
        }
        animationFrameId.current = requestAnimationFrame(() => {
            renderHighlights(HIGHLIGHT_ID, rangesRef.current);
        });
    }, []);

    const addHighlight = useCallback(
        (labelId: string, ranges: [number, number][]) => {
            rangesRef.current.set(labelId, ranges);
            onRenderHighlights();
        },
        [onRenderHighlights],
    );

    const removeHighlight = useCallback(
        (labelId: string) => {
            rangesRef.current.delete(labelId);
            onRenderHighlights();
        },
        [onRenderHighlights],
    );

    useEffect(() => {
        if (typeof CSS.highlights === 'undefined') {
            return;
        }

        return () => {
            CSS.highlights.delete(HIGHLIGHT_ID);
        };
    }, []);

    useEffect(() => {
        const wrapperEl =
            wrapperRef && 'current' in wrapperRef
                ? wrapperRef.current
                : wrapperRef;

        if (!wrapperEl) {
            return;
        }

        const observer = new MutationObserver(onRenderHighlights);

        observer.observe(wrapperEl, {
            childList: true,
            subtree: true,
            characterData: true,
        });

        return () => {
            observer.disconnect();
        };
    }, [wrapperRef, onRenderHighlights]);

    return (
        <HighlightContext.Provider
            value={{ addHighlight, removeHighlight, searchValue: inputValue }}
        >
            {children}
        </HighlightContext.Provider>
    );
}
HighlightedTextProvider.displayName = 'HighlightedTextProvider';

HighlightedTextProvider.displayName = 'HighlightedTextProvider';

export { HighlightedText, HighlightedTextProvider };
