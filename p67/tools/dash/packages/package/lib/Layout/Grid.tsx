import { baseDimension } from '@snowflake/balto-themes/baseDimension.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef, useContext } from 'react';
import { devError } from '../util/dev-warning';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';
import { GridContext } from './GridContext';
import { GridItem } from './GridItem';
import { LayoutContext } from './LayoutContext';
import { PageContext } from './PageContext';

interface GridProps<T extends keyof ReactHTML = 'div'>
    extends SlottedContainerProps<T> {
    /**
     * Whether the grid should grow.
     * @default false
     */
    grow?: boolean | undefined;
    /**
     * Whether the grid should shrink.
     * @default false
     */
    shrink?: boolean | undefined;
    /**
     * Whether the grid should have margin.
     * @default true
     */
    hasMargin?: boolean | undefined;
}
const styles = stylex.create({
    base: {
        containerType: 'inline-size', // Required to use @container query CSS styles on its children.
        display: 'flex',
        flexDirection: 'row',
        flexGrow: 0,
        flexShrink: 0,
        flexWrap: 'wrap',
        gap: tokens['space-gap-lg'],
        minHeight: 0,
        minWidth: 0,
    },
    centeredGrid: {
        marginInlineEnd: 'auto',
        marginInlineStart: 'auto',
        maxWidth: baseDimension.breakpointLarge,
        width: '100%',
    },
    regularGrid: {
        maxWidth: baseDimension.breakpointXlarge,
    },
    fullGrid: {},
    grow: {
        flexGrow: 1,
    },
    shrink: {
        flexShrink: 1,
    },
    withMargin: {
        marginInlineEnd: {
            default: tokens['space-horizontal-lg'],
            '@media (min-width: 1024px)': tokens['space-horizontal-3xl'],
        },
        marginInlineStart: {
            default: tokens['space-horizontal-lg'],
            '@media (min-width: 1024px)': tokens['space-horizontal-3xl'],
        },
    },
});

const GridComponent = forwardRef<HTMLElement, GridProps>(
    (props, forwardedRef) => {
        const gridContext = useContext(GridContext);
        const { variant } = useContext(PageContext);
        const layoutCtx = useContext(LayoutContext);
        if (!layoutCtx) {
            devError('Grid must be a child of Layout.Content');
        }
        const { grow, shrink, hasMargin = !gridContext, ...otherProps } = props;

        return (
            <GridContext.Provider value={true}>
                <SlottedContainer
                    {...otherProps}
                    tag="div"
                    stylexProps={stylex.props(
                        styles.base,
                        grow && styles.grow,
                        shrink && styles.shrink,
                        hasMargin && styles.withMargin,
                        variant === 'centered' && styles.centeredGrid,
                        variant === 'regular' && styles.regularGrid,
                        variant === 'full' && styles.fullGrid,
                    )}
                    ref={forwardedRef}
                />
            </GridContext.Provider>
        );
    },
);

GridComponent.displayName = 'Grid.Root';

export { GridComponent as Root, GridItem as Item };
export type { GridProps };
export type { GridItemProps, GridSize, GridSizeColumns } from './GridItem';
