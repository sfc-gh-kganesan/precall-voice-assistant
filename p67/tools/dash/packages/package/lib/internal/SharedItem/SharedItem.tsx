import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import {
    CheckBoldIcon,
    IconContextProvider,
    type IconType,
} from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes } from 'react';
import React, { forwardRef, useContext } from 'react';
import { mergeProps, useFocusRing } from 'react-aria';

import { useMergedStyles } from '../../hooks';
import { Flex } from '../../Layout';
import { HighlightedText, SizeContext } from '../../main';
import { OverflowTooltip } from '../../OverflowTooltip';
import { StatusBadge } from '../../Status';
import { TooltipContext } from '../../Tooltip/TooltipContext';
import type { SlottedLiContainerProps } from '../../util/SlottedContainer';
import { SlottedContainer } from '../../util/SlottedContainer';
import { useTypeRamp } from '../hooks/useTypeRamp';

interface SharedItemStatusSuffix {
    /**
     * The status of the shared item.
     */
    status: string;
}

type SharedItemSuffix =
    | SharedItemStatusSuffix
    | {
          /**
           * The icon of the shared item.
           */
          icon: IconType;
      }
    | React.ReactNode;
type SharedItemPrefix = IconType | React.ReactNode;

/**
 * Checks if the icon is an icon type.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function isIconType(icon: any): icon is IconType {
    return icon && typeof icon === 'object' && 'render' in icon;
}

interface SharedItemLabelProps extends HTMLAttributes<HTMLDivElement> {
    /**
     * The label of the shared item.
     */
    label: string;
    /**
     * The sublabel of the shared item.
     */
    subLabel?: string | undefined;
    /**
     * The disabled state of the shared item.
     */
    disabled?: boolean | undefined;
    /**
     * The selected state of the shared item.
     */
    selected?: boolean | undefined;
    /**
     * The prefix icon of the shared item.
     */
    prefixIcon?: SharedItemPrefix | undefined;
    /**
     * The suffix of the shared item.
     */
    suffix?: SharedItemSuffix | undefined;
}

const styles = stylex.create({
    wrapper: {
        backgroundColor: {
            ':hover': {
                ':not([data-disabled])': baltoTheme.reusableBackgroundRowHover,
            },
        },
        boxShadow: {
            ":is([data-focus-visible='true'])": `inset 0 0 0 2px ${baltoTheme.reusableBorderFocusedActiveItem}`,
        },
        cursor: {
            default: 'pointer',
            ':is([data-disabled])': 'not-allowed',
        },
        listStyle: 'none',
        outline: {
            default: 'none',
        },
    },
    container: {
        display: 'flex',
        flexDirection: 'row',
        flexGrow: 1,
        gap: tokens['space-gap-sm'],
        minWidth: 0,
        padding: `${tokens['space-vertical-sm']} ${tokens['space-horizontal-md']}`,
    },
    small: {
        gap: tokens['space-gap-2xs'],
        padding: `${tokens['space-vertical-2xs']} ${tokens['space-horizontal-md']}`,
    },
    labelContainer: {
        flexGrow: 1,
        minWidth: 0,
    },
    label: {
        // TODO: get menu item on type ramp.
        lineHeight: tokens['size-2xs'] /* 16 */,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
    },
    subLabel: {
        color: baltoTheme.reusableTextSecondary,
        wordBreak: 'break-word',
    },
    smallSubLabel: { fontSize: baltoTheme.fontSizeSmall },
    disabled: {
        color: baltoTheme.reusableDisabledText,
    },
    selected: {
        color: baltoTheme.reusableSelectedText,
    },
    critical: {
        color: baltoTheme.statusCriticalMessageText,
    },
    highlight: {
        backgroundColor: {
            '::highlight(highlighted-text)':
                baltoTheme.reusableSelectedBackground,
        },
        color: {
            '::highlight(highlighted-text)': baltoTheme.reusableSelectedText,
        },
    },
});

const Wrapper = forwardRef<HTMLLIElement, SlottedLiContainerProps>(
    function ListBoxItemWrapper({ ...props }, forwardedRef) {
        const { focusProps, isFocusVisible } = useFocusRing();

        return (
            <SlottedContainer
                tag="li"
                stylexProps={stylex.props(styles.wrapper)}
                {...mergeProps(props, focusProps)}
                data-focus-visible={isFocusVisible}
                data-item-wrapper={true}
                ref={forwardedRef}
            />
        );
    },
);

interface LabelProps extends SharedItemLabelProps {
    /**
     *
     */
    variant?: 'critical' | 'default' | undefined;
}

const Label = forwardRef<HTMLDivElement, LabelProps>(function ListBoxItemLabel(
    {
        label,
        subLabel,
        disabled,
        selected,
        prefixIcon: PrefixIcon,
        suffix,
        className,
        style,
        variant = 'default',
        ...props
    },
    forwardedRef,
) {
    const sizeContext = useContext(SizeContext);
    const labelIsAllCaps = label.toUpperCase() === label;
    const labelTextStyles = useTypeRamp(
        sizeContext === 'small'
            ? labelIsAllCaps
                ? 'allCapsSmall'
                : 'labelSmall'
            : labelIsAllCaps
              ? 'allCaps'
              : 'label',
    );
    const subLabelTextStyles = useTypeRamp('smallParagraph');
    const mergedStyles = useMergedStyles(
        className,
        style,
        stylex.props(
            styles.container,
            sizeContext === 'small' && styles.small,
            styles.highlight,
            variant === 'critical' && !disabled && styles.critical,
            disabled && styles.disabled,
        ),
    );

    return (
        <IconContextProvider
            color={
                !disabled && selected
                    ? baltoTheme.reusableSelectedText
                    : 'currentColor'
            }
        >
            <OverflowTooltip.Wrapper position="right">
                <div
                    ref={forwardedRef}
                    data-item-label={true}
                    {...props}
                    {...mergedStyles}
                >
                    {PrefixIcon &&
                        (isIconType(PrefixIcon) ? <PrefixIcon /> : PrefixIcon)}
                    <Flex
                        direction="column"
                        {...stylex.props(styles.labelContainer)}
                        gap="0_25x"
                    >
                        <OverflowTooltip.Text asChild>
                            <HighlightedText
                                data-label={true}
                                {...stylex.props(
                                    labelTextStyles,
                                    styles.label,
                                    disabled && styles.disabled,
                                    !disabled && selected && styles.selected,
                                )}
                            >
                                {label}
                            </HighlightedText>
                        </OverflowTooltip.Text>
                        {subLabel && (
                            <HighlightedText
                                {...stylex.props(
                                    subLabelTextStyles,
                                    sizeContext === 'small' &&
                                        styles.smallSubLabel,
                                    styles.subLabel,
                                    disabled && styles.disabled,
                                )}
                            >
                                {subLabel}
                            </HighlightedText>
                        )}
                    </Flex>
                    {React.isValidElement(suffix) ? (
                        suffix
                    ) : suffix &&
                      typeof suffix === 'object' &&
                      'status' in suffix ? (
                        <TooltipContext.Provider value={false}>
                            <StatusBadge>{suffix.status}</StatusBadge>
                        </TooltipContext.Provider>
                    ) : suffix &&
                      typeof suffix === 'object' &&
                      'icon' in suffix ? (
                        <suffix.icon />
                    ) : null}
                    {selected && <CheckBoldIcon />}
                </div>
            </OverflowTooltip.Wrapper>
        </IconContextProvider>
    );
});

const SharedItem = {
    Wrapper,
    Label,
};

export type { SharedItemLabelProps, SharedItemSuffix, SharedItemPrefix };
export { SharedItem };
