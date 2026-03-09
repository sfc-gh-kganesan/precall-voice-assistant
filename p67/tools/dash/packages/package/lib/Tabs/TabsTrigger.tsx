import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { baseColor } from '@snowflake/balto-themes/baseColor.stylex.js';
import * as stylex from '@stylexjs/stylex';
import type { CSSProperties } from 'react';
import { forwardRef } from 'react';
import { Tab } from 'react-aria-components';

import { CountBadge } from '../CountBadge';
import { useMergedStyles } from '../hooks';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { Flex } from '../Layout';

interface TabsTriggerProps
    extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onClick'> {
    /**
     * The value of the tabs trigger.
     */
    value: string;
    /**
     * Whether the tabs trigger is disabled.
     * @default false
     */
    disabled?: boolean | undefined;
    /**
     * An additional component to render after the label.
     */
    countBadge?: number | undefined;
    /**
     * The label of the tabs trigger.
     */
    label: string;
    /**
     * The children of the tabs trigger.
     */
    children?: never | undefined;
    /**
     * The class name of the tabs trigger.
     */
    className?: string | undefined;
    /**
     * The style of the tabs trigger.
     */
    style?: CSSProperties | undefined;
}

const styles = stylex.create({
    trigger: {
        alignItems: 'center',
        backgroundColor: baseColor.transparent,
        borderWidth: 0,
        color: {
            default: baltoTheme.reusableTextSecondary,
            ':hover:not([aria-selected=true])': baltoTheme.reusableTextPrimary,
            ':is([aria-selected=true])': baltoTheme.reusableSelectedUi,
            ':is([data-disabled])': baltoTheme.reusableDisabledText,
        },
        cursor: { default: 'pointer', ':is([data-disabled])': 'not-allowed' },
        display: 'flex',
        flexShrink: 0,
        height: '100%',
        justifyContent: 'center',
        padding: 0,
        position: 'relative',
        transitionDuration: '150ms',
        transitionProperty: 'color',
        transitionTimingFunction: 'ease-in-out',
    },
    border: {
        backgroundColor: {
            default: baseColor.transparent,
            ':is([data-hovered=true] *)': baltoTheme.reusableBorderBright,
            ':is([data-selected=true])': baltoTheme.reusableSelectedUi,
        },
        bottom: 0,
        height: 2,
        left: 0,
        position: 'absolute',
        right: 0,
        transitionDuration: '150ms',
        transitionProperty: 'background-color',
        transitionTimingFunction: 'ease-in-out',
    },
});

const TabsTrigger = forwardRef<HTMLButtonElement, TabsTriggerProps>(
    (props, forwardedRef) => {
        const {
            className,
            style,
            label,
            countBadge,
            value,
            disabled,
            ...otherProps
        } = props;
        const textStyles = useTypeRamp('labelSmall');
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.trigger, textStyles),
        );
        return (
            <Tab
                {...otherProps}
                {...styleProps}
                ref={forwardedRef}
                id={value}
                isDisabled={disabled}
            >
                {({ isSelected }) => (
                    <Flex gap="1x" align="center">
                        {label}{' '}
                        {countBadge && <CountBadge count={countBadge} />}
                        <div
                            {...stylex.props(styles.border)}
                            data-selected={isSelected}
                        />
                    </Flex>
                )}
            </Tab>
        );
    },
);
TabsTrigger.displayName = 'Tabs.Trigger';
export type { TabsTriggerProps };
export { TabsTrigger };
