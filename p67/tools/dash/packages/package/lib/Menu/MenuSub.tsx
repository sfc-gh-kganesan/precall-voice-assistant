import { ChevronRightIcon } from '@snowflake/stellar-icons';
import * as stylex from '@stylexjs/stylex';
import type { ReactNode } from 'react';
import { forwardRef } from 'react';
import { Menu, MenuItem, Popover, SubmenuTrigger } from 'react-aria-components';

import { BaltoThemeProvider } from '../BaltoProvider';
import type { SharedItemLabelProps } from '../internal/SharedItem/SharedItem';
import { SharedItem } from '../internal/SharedItem/SharedItem';
import { levelStyles } from '../internal/utils/levelStyles';
import type { ControlledOpenComponent } from '../util/Controlled';
import { menuStyles } from './internal/menuStyles';

interface MenuSubProps
    extends ControlledOpenComponent,
        Pick<
            SharedItemLabelProps,
            'label' | 'subLabel' | 'prefixIcon' | 'disabled'
        > {
    /**
     * The children of the submenu.
     */
    children: ReactNode;
}

const MenuSub = forwardRef<HTMLDivElement, MenuSubProps>(
    (props, forwardedRef) => {
        const { label, subLabel, disabled, prefixIcon, children } = props;

        return (
            <SubmenuTrigger>
                <SharedItem.Wrapper asChild>
                    <MenuItem isDisabled={disabled}>
                        <SharedItem.Label
                            label={label}
                            subLabel={subLabel}
                            disabled={disabled}
                            prefixIcon={prefixIcon}
                            suffix={{ icon: ChevronRightIcon }}
                        />
                    </MenuItem>
                </SharedItem.Wrapper>
                <Popover
                    ref={forwardedRef}
                    {...stylex.props(
                        levelStyles.level3Surface,
                        menuStyles.menuPopover,
                    )}
                >
                    <BaltoThemeProvider>
                        <Menu {...stylex.props(menuStyles.menuContainer)}>
                            {children}
                        </Menu>
                    </BaltoThemeProvider>
                </Popover>
            </SubmenuTrigger>
        );
    },
);

MenuSub.displayName = 'Menu.Sub';
export type { MenuSubProps };
export { MenuSub };
