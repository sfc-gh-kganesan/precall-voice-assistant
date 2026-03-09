import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef, useMemo } from 'react';

import { BreakpointValues } from '../types';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';

type GridSizeColumns = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12;
type GridItemSize = 'auto' | 'grow' | GridSizeColumns | false;

type BreakpointKey = (typeof BreakpointValues)[number];
type ResponsiveSize<T> = Partial<Record<BreakpointKey, T>>;
type ResponsiveStyleValue<T extends GridSizeColumns> = T | ResponsiveSize<T>;
interface GridItemProps<T extends keyof ReactHTML = 'div'>
    extends SlottedContainerProps<T> {
    /**
     * Defines the size of the the type `GridItem`.
     */
    size?: ResponsiveStyleValue<GridSizeColumns> | undefined;
}

const columnCount = 12;
const gapWidth = tokens['size-2xs'];
const columnWidth = `(100% - ${columnCount - 1} * ${gapWidth}) / ${columnCount}`;
const columnWidths = Array(columnCount)
    .fill(null)
    .map((_, i) => `calc(${i + 1} * ${columnWidth} + ${i} * ${gapWidth})`);
const styles = stylex.create({
    default: {
        display: 'flex',
        flexDirection: 'column',
    },
    dynamicWidth: (allBreakpoints: Record<BreakpointKey, GridSizeColumns>) => ({
        width: {
            '@container (max-width: 480px)':
                columnWidths[allBreakpoints.xs - 1],
            '@container (min-width: 480px) and (max-width: 720px)':
                columnWidths[allBreakpoints.sm - 1],
            '@container (min-width: 720px) and (max-width: 1024px)':
                columnWidths[allBreakpoints.md - 1],
            '@container (min-width: 1024px) and (max-width: 1360px)':
                columnWidths[allBreakpoints.lg - 1],
            '@container (min-width: 1360px)':
                columnWidths[allBreakpoints.xl - 1],
        },
    }),
});

const GridItem = forwardRef<HTMLElement, GridItemProps>(
    (props, forwardedRef) => {
        const { size, ...otherProps } = props;
        const allBreakpoints = useMemo((): Record<
            BreakpointKey,
            GridSizeColumns
        > => {
            if (typeof size === 'number') {
                return {
                    xs: size,
                    sm: size,
                    md: size,
                    lg: size,
                    xl: size,
                };
            }
            const firstKey = BreakpointValues.find(
                (key) => size?.[key] !== undefined,
            );
            if (!firstKey) {
                return {
                    xs: 12,
                    sm: 12,
                    md: 12,
                    lg: 12,
                    xl: 12,
                };
            }
            let prevKey: BreakpointKey = firstKey;
            return BreakpointValues.reduce(
                (acc, val) => {
                    if (size?.[val] !== undefined) {
                        acc[val] = size[val];
                        prevKey = val;
                    } else {
                        acc[val] = acc[prevKey];
                    }
                    return acc;
                },
                {} as Record<BreakpointKey, GridSizeColumns>,
            );
        }, [size]);

        return (
            <SlottedContainer
                {...otherProps}
                tag="div"
                stylexProps={stylex.props(
                    styles.default,
                    styles.dynamicWidth(allBreakpoints),
                )}
                ref={forwardedRef}
            />
        );
    },
);
GridItem.displayName = 'Grid.Item';
export { GridItem };
export type { GridItemProps, GridItemSize as GridSize, GridSizeColumns };
