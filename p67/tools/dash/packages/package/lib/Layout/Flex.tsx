import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef, useContext } from 'react';

import { SizeContext } from '../main';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';

type FlexDirection = 'row' | 'column' | 'row-reverse' | 'column-reverse';
type FlexAlign = 'start' | 'center' | 'end' | 'baseline' | 'stretch';
type FlexJustify = 'start' | 'center' | 'end' | 'between';
type FlexWrap = 'nowrap' | 'wrap' | 'wrap-reverse';
type FlexGap =
    | '0x'
    | '0_25x'
    | '0_5x'
    | '0_75x'
    | '1x'
    | '1_5x'
    | '2x'
    | '3x'
    | '4x'
    | '5x'
    | '6x'
    | '8x';

interface FlexProps<T extends keyof ReactHTML = 'div'>
    extends SlottedContainerProps<T> {
    /**
     * Whether the flex is inline.
     * @default false
     */
    inline?: boolean | undefined;
    /**
     * The direction of the flex.
     * @default "row"
     */
    direction?: FlexDirection | undefined;
    /**
     * The alignment of the flex.
     * @default "start"
     */
    align?: FlexAlign | undefined;
    /**
     * The justification of the flex.
     * @default "start"
     */
    justify?: FlexJustify | undefined;
    /**
     * The wrapping of the flex.
     * @default "nowrap"
     */
    wrap?: FlexWrap | undefined;
    /**
     * The gap of the flex.
     * @default "0_75x"
     */
    gap?: FlexGap | undefined;
    /**
     * The grow of the flex.
     */
    grow?: number | undefined;
    /**
     * The shrink of the flex.
     */
    shrink?: number | undefined;
    /**
     * The basis of the flex.
     */
    basis?: string | undefined;
}
const styles = stylex.create({
    common: {
        display: 'flex',
    },
    displayInlineFlex: {
        display: 'inline-flex',
    },
    directionRow: {
        flexDirection: 'row',
    },
    directionColumn: {
        flexDirection: 'column',
    },
    directionRowReverse: {
        flexDirection: 'row-reverse',
    },
    directionColumnReverse: {
        flexDirection: 'column-reverse',
    },
    alignStart: {
        alignItems: 'flex-start',
    },
    alignCenter: {
        alignItems: 'center',
    },
    alignEnd: {
        alignItems: 'flex-end',
    },
    alignBaseline: {
        alignItems: 'baseline',
    },
    alignStretch: {
        alignItems: 'stretch',
    },
    justifyStart: {
        justifyContent: 'flex-start',
    },
    justifyCenter: {
        justifyContent: 'center',
    },
    justifyEnd: {
        justifyContent: 'flex-end',
    },
    justifyBetween: {
        justifyContent: 'space-between',
    },
    wrap: {
        flexWrap: 'wrap',
    },
    wrapNo: {
        flexWrap: 'nowrap',
    },
    wrapReverse: {
        flexWrap: 'wrap-reverse',
    },
    gap0_25x: {
        gap: tokens['space-gap-3xs'],
    },
    gap0_5x: {
        gap: tokens['space-gap-2xs'],
    },
    gap0_75x: {
        gap: tokens['space-gap-xs'],
    },
    gap1x: {
        gap: tokens['space-gap-sm'],
    },
    gap1_5x: {
        gap: tokens['space-gap-md'],
    },
    gap2x: {
        gap: tokens['space-gap-lg'],
    },
    gap3x: {
        gap: tokens['space-gap-2xl'],
    },
    gap4x: {
        gap: tokens['space-gap-3xl'],
    },
    gap5x: {
        gap: tokens['space-gap-4xl'],
    },
    gap6x: {
        gap: tokens['space-gap-4xl'],
    },
    gap8x: {
        gap: tokens['space-gap-4xl'],
    },
    flexGrow: (grow: number) => ({
        flexGrow: grow,
        minWidth: 0,
    }),
    flexShrink: (shrink: number) => ({
        flexShrink: shrink,
    }),
    flexBasis: (basis: string) => ({
        flexBasis: basis,
    }),
});
const Flex = forwardRef<HTMLDivElement, FlexProps>((props, forwardedRef) => {
    const contextSize = useContext(SizeContext);
    const {
        inline = false,
        direction,
        align,
        justify,
        wrap,
        grow,
        shrink,
        basis,
        gap = contextSize === 'small' ? '0_75x' : '1x',
        ...restProps
    } = props;

    return (
        <SlottedContainer
            tag="div"
            stylexProps={stylex.props(
                styles.common,
                inline && styles.displayInlineFlex,
                direction === 'row' && styles.directionRow,
                direction === 'column' && styles.directionColumn,
                direction === 'row-reverse' && styles.directionRowReverse,
                direction === 'column-reverse' && styles.directionColumnReverse,
                align === 'start' && styles.alignStart,
                align === 'center' && styles.alignCenter,
                align === 'end' && styles.alignEnd,
                align === 'baseline' && styles.alignBaseline,
                align === 'stretch' && styles.alignStretch,
                justify === 'start' && styles.justifyStart,
                justify === 'center' && styles.justifyCenter,
                justify === 'end' && styles.justifyEnd,
                justify === 'between' && styles.justifyBetween,
                wrap === 'nowrap' && styles.wrapNo,
                wrap === 'wrap' && styles.wrap,
                wrap === 'wrap-reverse' && styles.wrapReverse,
                gap === '0_25x' && styles.gap0_25x,
                gap === '0_5x' && styles.gap0_5x,
                gap === '0_75x' && styles.gap0_75x,
                gap === '1x' && styles.gap1x,
                gap === '1_5x' && styles.gap1_5x,
                gap === '2x' && styles.gap2x,
                gap === '3x' && styles.gap3x,
                gap === '4x' && styles.gap4x,
                gap === '5x' && styles.gap5x,
                gap === '6x' && styles.gap6x,
                gap === '8x' && styles.gap8x,
                grow !== undefined && styles.flexGrow(grow),
                // Emulate flex: 1; which is flex: 1 1 0%;
                Boolean(
                    grow && shrink === undefined && basis === undefined,
                ) && [styles.flexShrink(1), styles.flexBasis('0%')],
                shrink !== undefined && styles.flexShrink(shrink),
                basis !== undefined && styles.flexBasis(basis),
            )}
            {...restProps}
            ref={forwardedRef}
        />
    );
});

Flex.displayName = 'Flex';

export { Flex };
export type { FlexProps, FlexDirection };
