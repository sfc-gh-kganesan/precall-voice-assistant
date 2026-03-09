import { useControlledState } from '@react-stately/utils';
import type { GlobalDOMAttributes } from '@react-types/shared';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { segmentedButtonTheme } from '@snowflake/balto-themes/segmentedButtonTheme.stylex.js';
import { IconContextProvider, type IconType } from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { CSSProperties, HTMLAttributes } from 'react';
import React, { forwardRef, useContext } from 'react';
import { ToggleButton, ToggleButtonGroup } from 'react-aria-components';

import { CountBadge } from '../CountBadge';
import { useMergedStyles } from '../hooks';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import type { Direction, Size } from '../types';
import type { ControlledValueComponent } from '../util/Controlled';
import { SizeContext } from '../util/context';

const ValueContext = React.createContext<string | undefined>(undefined);

const styles = stylex.create({
    root: {
        backgroundColor: segmentedButtonTheme.rootBackgroundDefault,
        borderRadius: tokens['radius-md'],
        height: tokens['size-md'],
        width: 'fit-content',

        alignItems: 'center',
        display: 'flex',
    },
    small: {
        height: tokens['size-sm'],
    },
    item: {
        borderColor: {
            default: 'transparent',
            ':is([data-selected=true])': baltoTheme.reusableBorderDefault,
        },
        borderRadius: tokens['radius-md'],
        borderStyle: 'solid',
        borderWidth: 1,

        alignItems: 'center',
        display: 'flex',
        gap: tokens['space-gap-sm'],

        backgroundColor: {
            default: 'transparent',
            ':is([data-selected=true])':
                segmentedButtonTheme.selectedItemBackgroundDefault,
        },
        color: {
            default: baltoTheme.reusableTextSecondary,
            ':is([data-selected=true])': baltoTheme.reusableSelectedUi,
            ':disabled': baltoTheme.reusableDisabledText,
        },
        cursor: { default: 'pointer', ':disabled': 'not-allowed' },
        height: '100%',
        padding: `0 ${tokens['space-horizontal-md']}`,
    },
});

interface SegmentedButtonProps
    extends Omit<HTMLAttributes<HTMLDivElement>, 'defaultValue' | 'dir'>,
        ControlledValueComponent<string> {
    /**
     * The children of the segmented button.
     */
    children: React.ReactNode;
    /**
     * The size of the segmented button.
     * @default "regular"
     */
    size?: Extract<Size, 'small' | 'regular'> | undefined;
    /**
     * The direction of the segmented button.
     * @default "ltr"
     */
    dir?: Direction | undefined;
}

const SegmentedButtonRoot = forwardRef<HTMLDivElement, SegmentedButtonProps>(
    function SegmentedButton(props, ref) {
        const contextSize = useContext(SizeContext);
        const {
            className,
            style,
            size = contextSize ?? 'regular',
            value: valueProp,
            defaultValue,
            onValueChange: onValueChangeProp,
            ...otherProps
        } = props;
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.root, size === 'small' && styles.small),
        );
        const [value, onValueChange] = useControlledState(
            valueProp,
            defaultValue || '',
            onValueChangeProp
                ? (newValue) => {
                      if (!newValue) return;
                      onValueChangeProp?.(newValue as string);
                  }
                : undefined,
        );

        return (
            <ValueContext.Provider value={value}>
                <ToggleButtonGroup
                    ref={ref}
                    selectionMode="single"
                    selectedKeys={[value]}
                    onSelectionChange={(newSelection) => {
                        const arr = Array.from(newSelection.values());
                        onValueChange(arr[0] as string);
                    }}
                    {...otherProps}
                    {...styleProps}
                />
            </ValueContext.Provider>
        );
    },
);

SegmentedButtonRoot.displayName = 'SegmentedButton.Root';

interface SegmentedButtonItemProps
    extends Omit<GlobalDOMAttributes<HTMLDivElement>, 'onClick'> {
    /**
     * The children of the segmented button item.
     */
    children: React.ReactNode;
    /**
     * The value of the segmented button item.
     */
    value: string;
    /**
     * The icon of the segmented button item.
     */
    icon?: IconType | undefined;
    /**
     * The badge count of the segmented button item.
     */
    countBadge?: number | undefined;
    /**
     * Whether the segmented button item is disabled.
     */
    disabled?: boolean | undefined;
    /**
     * The class name of the segmented button item.
     */
    className?: string | undefined;
    /**
     * The style of the segmented button item.
     */
    style?: CSSProperties | undefined;
}

const Item = forwardRef<HTMLButtonElement, SegmentedButtonItemProps>(
    function SegmentedButtonItem(
        {
            className,
            style,
            disabled,
            icon: Icon,
            children,
            countBadge,
            value,
            ...props
        },
        ref,
    ) {
        const isSelected = useContext(ValueContext) === value;
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.item, useTypeRamp('label')),
        );

        return (
            <ToggleButton
                ref={ref}
                {...props}
                {...styleProps}
                id={value}
                isDisabled={disabled}
            >
                {Icon && (
                    <IconContextProvider
                        color={
                            disabled
                                ? baltoTheme.reusableDisabledText
                                : isSelected
                                  ? baltoTheme.reusableSelectedUi
                                  : baltoTheme.reusableTextSecondary
                        }
                    >
                        <Icon />
                    </IconContextProvider>
                )}
                {children}
                {typeof countBadge === 'number' && countBadge > 0 && (
                    <CountBadge count={countBadge} />
                )}
            </ToggleButton>
        );
    },
);

Item.displayName = 'SegmentedButton.Item';

export type { SegmentedButtonProps, SegmentedButtonItemProps };
export { SegmentedButtonRoot as Root, Item };
