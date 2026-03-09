import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type React from 'react';
import type { ReactHTML } from 'react';
import { forwardRef, useContext } from 'react';
import { Separator } from 'react-aria-components';

import { useMergedStyles } from '../hooks';
import { SizeContext } from '../main';

type MenuDividerProps<T extends keyof ReactHTML = 'div'> = Omit<
    React.ComponentProps<T>,
    'children'
>;

const styles = stylex.create({
    separator: {
        backgroundColor: baltoTheme.reusableBorderDefault,
        height: 1,
        margin: `${tokens['space-vertical-sm']} 0`,
    },
    small: {
        margin: `${tokens['space-vertical-3xs']} 0`,
    },
});

const MenuDivider = forwardRef<HTMLDivElement, MenuDividerProps>(
    (props, forwardedRef) => {
        const sizeContext = useContext(SizeContext);
        const { className, style, ...otherProps } = props;
        return (
            <Separator
                {...otherProps}
                ref={forwardedRef}
                {...useMergedStyles(
                    className,
                    style,
                    stylex.props(
                        styles.separator,
                        sizeContext === 'small' && styles.small,
                    ),
                )}
            />
        );
    },
);
MenuDivider.displayName = 'Menu.Divider';
export type { MenuDividerProps };
export { MenuDivider };
