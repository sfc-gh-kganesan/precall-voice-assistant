import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { toolbarTheme } from '@snowflake/balto-themes/toolbarTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes, Ref } from 'react';
import { createContext, forwardRef, useContext } from 'react';
import {
    Button as AriaButton,
    Toolbar as ToolbarPrimitive,
} from 'react-aria-components';

import type { ButtonProps, IconButtonProps } from '../Button';
import {
    Button as ButtonPrimitive,
    IconButton as IconButtonPrimitive,
} from '../Button';
import { Divider as DividerPrimitive } from '../Divider';
import { Flex } from '../Layout';
import { useMergedStyles } from '../main';
import { Tooltip } from '../Tooltip';

const DirectionContext = createContext<'horizontal' | 'vertical'>('horizontal');

const styles = stylex.create({
    root: {
        alignItems: 'center',
        backgroundColor: baltoTheme.surfaceLevel_1Background,
        borderColor: toolbarTheme.borderColorDefault,
        borderRadius: toolbarTheme.borderRadiusDefault,
        borderStyle: toolbarTheme.borderStyleDefault,
        borderWidth: toolbarTheme.borderWidthDefault,
        boxShadow: toolbarTheme.boxShadowDefault,
        display: 'flex',
        padding: tokens['space-vertical-3xs'],
        width: 'fit-content',
    },
    vertical: {
        flexDirection: 'column',
    },
    divider: {
        alignSelf: 'stretch',
        padding: `${tokens['space-vertical-xs']} ${tokens['space-horizontal-sm']}`,
    },
    dividerVertical: {
        padding: `${tokens['space-vertical-sm']} ${tokens['space-horizontal-xs']}`,
    },
});

interface ToolbarProps extends Omit<HTMLAttributes<HTMLDivElement>, 'dir'> {
    /**
     * The direction of the toolbar.
     * @default "horizontal"
     */
    direction?: 'horizontal' | 'vertical' | undefined;
}

const ToolbarRoot = forwardRef<HTMLDivElement, ToolbarProps>(function Toolbar(
    { direction = 'horizontal', className, style, ...props },
    ref,
) {
    const styleProps = useMergedStyles(
        className,
        style,
        stylex.props(styles.root, direction === 'vertical' && styles.vertical),
    );

    return (
        <DirectionContext.Provider value={direction}>
            <ToolbarPrimitive
                orientation={direction}
                ref={ref}
                {...styleProps}
                {...props}
            />
        </DirectionContext.Provider>
    );
});

ToolbarRoot.displayName = 'Toolbar.Root';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type DistributiveOmit<T, U> = T extends any
    ? Pick<T, Exclude<keyof T, U>>
    : never;

type ToolbarIconButtonProps = DistributiveOmit<
    IconButtonProps,
    'variant' | 'aria-label'
> & {
    /**
     * The text of the icon button.
     */
    text: string;
    /**
     * The aria label of the icon button.
     */
    'aria-label'?: string | undefined;
    /**
     * Whether the tooltip is open.
     */
    tooltipOpen?: boolean | undefined;
    /**
     * A callback for when the tooltip is opened.
     */
    onTooltipOpenChange?: ((open: boolean) => void) | undefined;
    /**
     * The default open state of the tooltip.
     */
    defaultTooltipOpen?: boolean | undefined;
};

const IconButton = forwardRef(function IconButton(
    {
        text,
        tooltipOpen,
        onTooltipOpenChange,
        defaultTooltipOpen,
        children,
        asChild,
        ...props
    }: ToolbarIconButtonProps,
    ref?: Ref<HTMLButtonElement>,
) {
    const direction = useContext(DirectionContext);
    return (
        <Tooltip
            text={text}
            open={tooltipOpen}
            onOpenChange={onTooltipOpenChange}
            defaultOpen={defaultTooltipOpen}
            position={direction === 'vertical' ? 'right' : 'top'}
        >
            <IconButtonPrimitive
                variant="tertiary"
                ref={ref}
                aria-label={text}
                asChild
                {...props}
            >
                {asChild ? children : <AriaButton>{children}</AriaButton>}
            </IconButtonPrimitive>
        </Tooltip>
    );
});

IconButton.displayName = 'Toolbar.IconButton';

const Button = forwardRef(function Button(
    { children, ...props }: Omit<ButtonProps, 'variant'>,
    ref?: Ref<HTMLButtonElement>,
) {
    return (
        <ButtonPrimitive asChild variant="tertiary" ref={ref} {...props}>
            <AriaButton>{children}</AriaButton>
        </ButtonPrimitive>
    );
});

Button.displayName = 'Toolbar.Button';
type ToolbarDividerProps = HTMLAttributes<HTMLHRElement>;

const Divider = forwardRef(function Divider(
    { className, style, ...props }: ToolbarDividerProps,
    ref?: Ref<HTMLHRElement>,
) {
    const toolbarDirection = useContext(DirectionContext);
    const direction =
        toolbarDirection === 'vertical' ? 'horizontal' : 'vertical';
    const styleProps = useMergedStyles(
        className,
        style,
        stylex.props(
            styles.divider,
            direction === 'vertical' && styles.dividerVertical,
        ),
    );

    return (
        <Flex {...props} {...styleProps}>
            <DividerPrimitive ref={ref} direction={direction} {...props} />
        </Flex>
    );
});

Divider.displayName = 'Toolbar.Divider';

export type { ToolbarProps, ToolbarIconButtonProps, ToolbarDividerProps };
export { ToolbarRoot as Root, IconButton, Button, Divider };
