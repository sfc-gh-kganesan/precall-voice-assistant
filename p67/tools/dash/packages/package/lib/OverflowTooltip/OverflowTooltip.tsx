import { createContext } from '@radix-ui/react-context';
import { Slot } from '@radix-ui/react-slot';
import { mergeProps, useEffectEvent } from '@react-aria/utils';
import { useControlledState } from '@react-stately/utils';
import * as stylex from '@stylexjs/stylex';
import type { Ref } from 'react';
import { forwardRef, useContext, useEffect, useRef, useState } from 'react';
import { useSize } from 'use-shared-resize-observer/use-size';

import { useMergedRef } from '../internal/hooks/useMergedRef';
import type { SlottedContainerProps } from '../main';
import { SlottedContainer, useBaltoContext } from '../main';
import type { TooltipProps } from '../Tooltip/Tooltip';
import { Tooltip } from '../Tooltip/Tooltip';
import { TooltipContext } from '../Tooltip/TooltipContext';

const styles = stylex.create({
    overflowTooltip: {
        display: 'inline-block',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
    },
});

/**
 * Calculates the width of a text element.
 */
function textWidth(el: HTMLSpanElement, container: HTMLElement | null) {
    el.style.width = 'max-content';
    el.style.overflow = 'visible';
    el.style.visibility = 'hidden';

    (container || document.body).appendChild(el);
    const result = el.clientWidth;
    (container || document.body).removeChild(el);

    return result;
}

const [OverflowTooltipTextContext, useOverflowTooltipTextContext] =
    createContext<{
        /**
         * The ref of the text element.
         */
        textRef: Ref<HTMLSpanElement>;
    }>('OverflowTooltip.Wrapper');

type SupportedTooltipProps = Pick<
    TooltipProps,
    'position' | 'defaultOpen' | 'open' | 'onOpenChange'
>;

interface OverflowTooltipWrapperProps extends SupportedTooltipProps {
    /**
     * The children of the overflow tooltip wrapper.
     */
    children: React.ReactElement;
}

/**
 * This sub-component is used to display the tooltip.
 * It should be composed with the `OverflowTooltip.Text`.
 * Simple cases can be handled but just using `OverflowTooltip`
 *
 * @example
 * <OverflowTooltip.Wrapper>
 *   <Flex>
 *     <PlusIcon />
 *     <OverflowTooltip.Text>
 *       Something with really really really really really really long text
 *     </OverflowTooltip.Text>
 *   </Flex>
 * </OverflowTooltip.Wrapper>
 */
const OverflowTooltipWrapper = forwardRef<
    HTMLSpanElement,
    OverflowTooltipWrapperProps
>(
    (
        {
            children,
            open: openProp,
            defaultOpen,
            onOpenChange,
            position,
            ...props
        },
        ref,
    ) => {
        const { portalContainer } = useBaltoContext();
        const textRef = useRef<HTMLSpanElement>(null);
        const hasTooltipParent = useContext(TooltipContext);
        const [needsTooltip, setNeedsTooltip] = useState(false);
        const [text, setText] = useState(
            typeof children === 'string' ? children : '',
        );
        const [open, setOpen] = useControlledState(
            openProp,
            defaultOpen ?? false,
            onOpenChange,
        );
        const size = useSize(textRef);

        const onPointerLeave = useEffectEvent(() => setOpen(false));
        const onPointerEnter = useEffectEvent(() => {
            if (!textRef.current) return;

            const clonedText = textRef.current.cloneNode(
                true,
            ) as HTMLSpanElement;
            clonedText.style.maxWidth = 'max-content';
            const width = textWidth(
                clonedText,
                textRef.current.parentElement || portalContainer,
            );
            const needsTooltip = width > Math.ceil(size.width);

            setNeedsTooltip(needsTooltip);

            if (needsTooltip) {
                setOpen(true);
            }
        });

        useEffect(() => {
            if (defaultOpen) {
                onPointerEnter();
            }
        }, [defaultOpen, onPointerEnter]);

        useEffect(() => {
            if (typeof children !== 'string') {
                // Reading textContent does not trigger a reflow, while reading innerText does.
                setText(textRef.current?.textContent || '');
            }
        }, [children]);

        const content = (
            <Slot
                ref={ref}
                {...mergeProps(props, { onPointerEnter, onPointerLeave })}
            >
                {children}
            </Slot>
        );

        if (hasTooltipParent) {
            return (
                <OverflowTooltipTextContext textRef={textRef}>
                    {content}
                </OverflowTooltipTextContext>
            );
        }

        return (
            <OverflowTooltipTextContext textRef={textRef}>
                <Tooltip
                    text={text}
                    open={open}
                    onOpenChange={setOpen}
                    position={position}
                    disabled={!needsTooltip}
                >
                    {content}
                </Tooltip>
            </OverflowTooltipTextContext>
        );
    },
);

OverflowTooltipWrapper.displayName = 'OverflowTooltip.Wrapper';
type OverflowTooltipTextProps = SlottedContainerProps<'span'>;
/**
 * A sub-component of `OverflowTooltip` that is used when the children of the Overflow tooltip is complex JSX.
 *
 * This component is used to get the text content to display in the tooltip.
 *
 * @example
 * <OverflowTooltip.Wrapper>
 *   <Flex>
 *     <PlusIcon />
 *     <OverflowTooltip.Text>
 *       Something with really really really really really really long text
 *     </OverflowTooltip.Text>
 *   </Flex>
 * </OverflowTooltip.Wrapper>
 */
const OverflowTooltipText = forwardRef<
    HTMLSpanElement,
    OverflowTooltipTextProps
>((props, outerRef) => {
    const { textRef } = useOverflowTooltipTextContext('OverflowTooltip.Text');
    const mergedRef = useMergedRef(textRef, outerRef);

    return (
        // The JSX might have elements nested and we don't want those to believe they are tooltip triggers.
        // ex: A Drawer nested within a SingleLine.
        <TooltipContext.Provider value={false}>
            <SlottedContainer
                tag="span"
                ref={mergedRef}
                stylexProps={stylex.props(styles.overflowTooltip)}
                {...props}
            />
        </TooltipContext.Provider>
    );
});

OverflowTooltipText.displayName = 'OverflowTooltip.Text';

interface OverflowTooltipProps
    extends SlottedContainerProps<'span'>,
        SupportedTooltipProps {}

const OverflowTooltipImpl = forwardRef<HTMLSpanElement, OverflowTooltipProps>(
    ({ position, defaultOpen, open, onOpenChange, ...props }, ref) => {
        return (
            <OverflowTooltipWrapper
                ref={ref}
                position={position}
                defaultOpen={defaultOpen}
                open={open}
                onOpenChange={onOpenChange}
            >
                <OverflowTooltipText ref={ref} {...props} />
            </OverflowTooltipWrapper>
        );
    },
);

OverflowTooltipImpl.displayName = 'OverflowTooltip.Root';

export {
    OverflowTooltipImpl as Root,
    OverflowTooltipText as Text,
    OverflowTooltipWrapper as Wrapper,
};
export type { OverflowTooltipWrapperProps, OverflowTooltipTextProps };
