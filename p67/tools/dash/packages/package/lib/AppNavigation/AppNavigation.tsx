import { Slottable } from '@radix-ui/react-slot';
import { useEffectEvent, useLayoutEffect } from '@react-aria/utils';
import { useControlledState } from '@react-stately/utils';
import { appNavigationTheme } from '@snowflake/balto-themes/appNavigationTheme.stylex.js';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import {
    CheckBoldIcon,
    ChevronUpIcon,
    IconContextProvider,
    SnowflakeIcon,
} from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type React from 'react';
import type { Ref } from 'react';
import { createContext, forwardRef, useContext, useRef } from 'react';

import { useMergedRef } from '../internal/hooks/useMergedRef';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import type {
    ControlledOpenComponent,
    MenuItemProps,
    SlottedContainerProps,
} from '../main';
import {
    Flex,
    Menu,
    OverflowTooltip,
    SlottedContainer,
    Tooltip,
    useMergedStyles,
} from '../main';
import { TooltipContext } from '../Tooltip/TooltipContext';
import { SnowFlakeWordMark } from './SnowFlakeWordMark';

const NestedItemContext = createContext(0);
const CollapsedContext = createContext(false);
const AsMenuContext = createContext(false);
const InListContext = createContext(false);

const styles = stylex.create({
    root: {
        backgroundColor: appNavigationTheme.sidebarBackgroundDefault,
        borderRightColor: baltoTheme.surfaceLevel_2Border,
        borderRightStyle: 'solid',
        borderRightWidth: 1,
        display: 'flex',
        flexDirection: 'column',
        gap: tokens['space-gap-sm'],
        height: '100%',
        overflow: 'auto',
        padding: `${tokens['space-vertical-lg']} ${tokens['space-horizontal-lg']} 0`,
        width: 240,
    },
    collapsed: {
        alignItems: 'center',
        padding: `${tokens['space-vertical-lg']} ${tokens['space-horizontal-sm']} 0`,
        width: 80,
    },
    logo: {
        padding: `${tokens['space-vertical-sm']} 0 ${tokens['space-vertical-md']} ${tokens['space-horizontal-sm']}`,
    },
    logoCollapsed: {
        paddingLeft: 0,
    },
    body: {
        display: 'flex',
        flexDirection: 'column',
        flexGrow: 1,
    },
    bodyCollapsed: {
        alignItems: 'center',
    },
    navList: { listStyle: 'none', margin: 0, padding: 0 },
    navItem: {
        alignItems: 'center',
        display: 'flex',
        gap: tokens['space-gap-lg'],

        borderRadius: tokens['radius-md'],
        borderWidth: 0,
        cursor: 'pointer',
        flexGrow: 1,
        height: tokens['size-md'],
        margin: `${tokens['space-vertical-2xs']} 0`,
        minWidth: 0,
        overflow: 'hidden',
        padding: `0 ${tokens['space-horizontal-lg']}`,
        textAlign: 'left',
        textDecoration: 'none',
        userSelect: 'none',

        backgroundColor: {
            default: 'transparent',
            ":is([aria-current='page'])": baltoTheme.reusableSelectedBackground,
            ":hover:not([aria-current='page'])":
                appNavigationTheme.itemBackgroundHover,
        },

        color: {
            default: baltoTheme.reusableTextSecondary,
            ":is([aria-current='page'])": baltoTheme.reusableSelectedText,
        },
    },
    navItemCollapsed: {
        flex: 'none',
        justifyContent: 'center',
        padding: `0 ${tokens['space-horizontal-sm']}`,
        width: tokens['size-lg'],
    },
    srOnly: {
        clip: 'rect(0 0 0 0)',
        clipPath: 'inset(50%)',
        height: 1,
        overflow: 'hidden',
        position: 'absolute',
        whiteSpace: 'nowrap',
        width: 1,
    },
    group: {},
    groupSummary: {
        alignItems: 'center',
        display: 'flex',
        gap: '2x',
    },
    userMenuTrigger: {
        backgroundColor: {
            default: 'transparent',
            ":is([data-state='open'])": baltoTheme.reusableSelectedBackground,
            ':hover': baltoTheme.reusableBackgroundRowHover,
        },
        borderRadius: tokens['radius-md'],
        borderWidth: 0,
        height: 55,
        padding: `${tokens['space-vertical-sm']} ${tokens['space-horizontal-md']}`,
        textAlign: 'left',
        userSelect: 'none',
    },
    userMenuTriggerCollapsed: {
        padding: `${tokens['space-vertical-md']} ${tokens['space-horizontal-sm']}`,
    },
    userMenuTriggerLabel: {
        flexGrow: 1,
        minWidth: 0,
    },
    userMenuHeader: {
        padding: `${tokens['space-vertical-2xs']} ${tokens['space-horizontal-lg']}`,
    },
    userMenuHeaderLabel: {
        flexGrow: 1,
        minWidth: 0,
        padding: `0 ${tokens['space-horizontal-3xs']}`,
    },
    secondaryText: {
        color: baltoTheme.reusableTextSecondary,
    },
    hidden: {
        display: 'none',
    },
    footer: {
        backgroundColor: appNavigationTheme.sidebarBackgroundDefault,
        bottom: 0,
        padding: `${tokens['space-vertical-lg']}  0`,
        position: 'sticky',
    },
});

interface AppNavigationProps extends React.HTMLAttributes<HTMLDivElement> {
    /**
     * Whether the app navigation is collapsed.
     * @default false
     */
    isCollapsed?: boolean | undefined;
}

const Root = forwardRef<HTMLDivElement, AppNavigationProps>(
    function AppNavigation({ className, style, isCollapsed, ...props }, ref) {
        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(styles.root, isCollapsed && styles.collapsed),
        );
        return (
            <CollapsedContext.Provider value={isCollapsed ?? false}>
                <div ref={ref} {...props} {...mergedStyles} />
            </CollapsedContext.Provider>
        );
    },
);

Root.displayName = 'AppNavigation';

const Body = forwardRef<HTMLUListElement, React.ComponentPropsWithoutRef<'ul'>>(
    function AppNavigationBody({ className, style, ...props }, ref) {
        const isCollapsed = useContext(CollapsedContext);
        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(
                styles.body,
                styles.navList,
                isCollapsed && styles.bodyCollapsed,
            ),
        );

        return (
            <InListContext.Provider value={true}>
                <ul ref={ref} {...props} {...mergedStyles} />
            </InListContext.Provider>
        );
    },
);

Body.displayName = 'AppNavigation.Body';

interface AppNavigationLogoProps
    extends Omit<React.HTMLAttributes<HTMLDivElement>, 'children'> {
    /**
     * The logo of the app navigation.
     */
    logo: React.ReactNode;
    /**
     * The logo of the app navigation for mobile devices.
     */
    mobileLogo: React.ReactNode;
    /**
     * The children of the app navigation logo.
     */
    children?: never | undefined;
}

const Logo = forwardRef<HTMLDivElement, AppNavigationLogoProps>(
    function AppNavigationLogo(
        { className, style, mobileLogo, logo, ...props },
        ref,
    ) {
        const isCollapsed = useContext(CollapsedContext);
        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(styles.logo, isCollapsed && styles.logoCollapsed),
        );

        return (
            <Flex {...mergedStyles} {...props} ref={ref}>
                {isCollapsed ? mobileLogo : logo}
            </Flex>
        );
    },
);

Logo.displayName = 'AppNavigation.Logo';

const SnowflakeLogo = forwardRef<
    HTMLDivElement,
    Omit<React.HTMLAttributes<HTMLDivElement>, 'children'>
>(function SnowflakeLogo(props, ref) {
    return (
        <Logo
            {...props}
            ref={ref}
            logo={<SnowFlakeWordMark />}
            mobileLogo={
                <IconContextProvider size={tokens['size-md']} color="#29B5E8">
                    <SnowflakeIcon />
                </IconContextProvider>
            }
        />
    );
});

SnowflakeLogo.displayName = 'AppNavigation.Logo';

interface AppNavigationNavItemProps extends SlottedContainerProps<'button'> {
    /**
     * The icon of the app navigation item.
     */
    icon?: React.ReactNode | undefined;
    /**
     * The label of the app navigation item.
     */
    label: string;
    /**
     * Whether the app navigation item is active.
     */
    isActive?: boolean | undefined;
}

const NavItem = forwardRef<HTMLButtonElement, AppNavigationNavItemProps>(
    function AppNavigationNavItem(
        { icon, isActive, label, ...props },
        outerRef,
    ) {
        const innerRef = useRef<HTMLButtonElement>(null);
        const ref = useMergedRef(outerRef, innerRef);
        const level = useContext(NestedItemContext);
        const isCollapsed = useContext(CollapsedContext);
        const isInMenu = useContext(AsMenuContext);
        const isInList = useContext(InListContext);
        const textStyles = useTypeRamp(
            level ? 'smallParagraphBold' : 'boldSingleLine',
        );

        const iconEl = icon && (
            <IconContextProvider>
                <Flex data-icon align="center" justify="center">
                    {icon}
                </Flex>
            </IconContextProvider>
        );

        const scrollIntoView = useEffectEvent(() => {
            if (isInMenu || !isActive) {
                return;
            }

            const element = innerRef.current;

            if (element) {
                if ('scrollIntoViewIfNeeded' in element) {
                    (
                        element.scrollIntoViewIfNeeded as typeof element.scrollIntoView
                    )({
                        behavior: 'instant',
                    });
                } else {
                    element.scrollIntoView({ behavior: 'instant' });
                }
            }
        });

        // Ensure the active item is visible when the component mounts
        useLayoutEffect(scrollIntoView, [scrollIntoView]);

        if (isInMenu) {
            return (
                <Menu.Item
                    {...(props as MenuItemProps)}
                    ref={ref as Ref<HTMLLIElement>}
                    label={label}
                    prefixIcon={iconEl}
                    suffix={isActive && <CheckBoldIcon />}
                />
            );
        }

        const children = props.asChild ? props.children : label;
        const item = (
            <SlottedContainer
                tag="button"
                {...props}
                ref={ref}
                aria-current={isActive ? 'page' : undefined}
                stylexProps={stylex.props(
                    styles.navItem,
                    textStyles,
                    isCollapsed && styles.navItemCollapsed,
                )}
                style={{
                    marginLeft: level
                        ? `calc(${tokens['size-md']} * ${level})`
                        : 0,
                }}
            >
                {iconEl}
                <Slottable>
                    {isCollapsed ? (
                        <span {...stylex.props(styles.srOnly)}>{children}</span>
                    ) : (
                        children
                    )}
                </Slottable>
            </SlottedContainer>
        );

        return (
            <Flex asChild align="center">
                <Tooltip disabled={!isCollapsed} text={label} position="right">
                    {isInList ? <li>{item}</li> : <span>{item}</span>}
                </Tooltip>
            </Flex>
        );
    },
);
NavItem.displayName = 'AppNavigation.NavItem';

interface AppNavigationGroupProps
    extends React.HTMLAttributes<HTMLLIElement>,
        ControlledOpenComponent {
    /**
     * The icon of the app navigation group.
     */
    icon?: React.ReactNode | undefined;
    /**
     * The label of the app navigation group.
     */
    label: string;
}

const Group = forwardRef<HTMLLIElement, AppNavigationGroupProps>(
    function AppNavigationGroup(
        {
            className,
            style,
            icon,
            label,
            children,
            open: openProp,
            onOpenChange,
            defaultOpen,
            ...props
        },
        ref,
    ) {
        const isCollapsed = useContext(CollapsedContext);
        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(styles.group),
        );
        const level = useContext(NestedItemContext);
        const textStyles = useTypeRamp(
            level > 0 ? 'smallParagraphBold' : 'boldSingleLine',
        );
        const [open, setOpen] = useControlledState(
            openProp,
            defaultOpen ?? false,
            onOpenChange,
        );
        const isInMenu = useContext(AsMenuContext);

        if (isInMenu) {
            return (
                <Menu.Sub label={label}>
                    <AsMenuContext.Provider value={true}>
                        {children}
                    </AsMenuContext.Provider>
                </Menu.Sub>
            );
        }

        if (isCollapsed) {
            return (
                <Flex asChild direction="column" gap="0x">
                    <Menu.Root
                        position="right"
                        trigger={
                            <Tooltip
                                disabled={!isCollapsed}
                                text={label}
                                position="right"
                            >
                                <li ref={ref} {...props} {...mergedStyles}>
                                    <span
                                        {...stylex.props(
                                            styles.groupSummary,
                                            styles.navItem,
                                            styles.navItemCollapsed,
                                            textStyles,
                                        )}
                                    >
                                        <Flex gap="2x" align="center">
                                            <IconContextProvider>
                                                {icon}
                                            </IconContextProvider>
                                            <span
                                                {...stylex.props(styles.srOnly)}
                                            >
                                                {label}
                                            </span>
                                        </Flex>
                                    </span>
                                </li>
                            </Tooltip>
                        }
                    >
                        <AsMenuContext.Provider value={true}>
                            {children}
                        </AsMenuContext.Provider>
                    </Menu.Root>
                </Flex>
            );
        }

        return (
            <Flex asChild direction="column" gap="0x">
                <li ref={ref} {...props} {...mergedStyles}>
                    <details open={open}>
                        <summary
                            {...stylex.props(
                                styles.groupSummary,
                                styles.navItem,
                                textStyles,
                            )}
                            onClick={(e) => {
                                e.preventDefault();
                                setOpen(!open);
                            }}
                            style={{
                                marginLeft: `calc(${tokens['space-horizontal-3xl']} * ${level})`,
                                paddingLeft:
                                    level > 0 ? tokens['size-2xs'] : undefined,
                            }}
                        >
                            <Flex gap="2x" align="center">
                                <IconContextProvider>
                                    {icon}
                                </IconContextProvider>
                                {label}
                            </Flex>
                        </summary>
                        <TooltipContext.Provider value={false}>
                            <NestedItemContext.Provider value={level + 1}>
                                {children}
                            </NestedItemContext.Provider>
                        </TooltipContext.Provider>
                    </details>
                </li>
            </Flex>
        );
    },
);

Group.displayName = 'AppNavigation.Group';

const Footer = forwardRef<
    HTMLDivElement,
    React.ComponentPropsWithoutRef<'div'>
>(({ className, style, ...props }, ref) => {
    const mergedStyles = useMergedStyles(
        className,
        style,
        stylex.props(styles.footer),
    );

    return (
        <Flex
            ref={ref}
            direction="column"
            gap="0x"
            {...props}
            {...mergedStyles}
        />
    );
});

Footer.displayName = 'AppNavigation.Footer';

interface AppNavigationUserMenuTriggerProps
    extends React.HTMLAttributes<HTMLButtonElement> {
    /**
     * The label of the app navigation user menu trigger.
     */
    label: string;
    /**
     * The sub label of the app navigation user menu trigger.
     */
    subLabel: string;
    /**
     * The avatar of the app navigation user menu trigger.
     */
    avatar?: React.ReactNode | undefined;
}

const UserMenuTrigger = forwardRef<
    HTMLButtonElement,
    AppNavigationUserMenuTriggerProps
>(function AppNavigationUserMenuTrigger(
    { className, style, avatar, label, subLabel, ...props },
    ref,
) {
    const isCollapsed = useContext(CollapsedContext);
    const mergedStyles = useMergedStyles(
        className,
        style,
        stylex.props(styles.userMenuTrigger),
    );
    const labelStyles = useTypeRamp('labelSmall');

    return (
        <Flex asChild align="center">
            <button ref={ref} {...props} {...mergedStyles}>
                {avatar}
                {!isCollapsed && (
                    <>
                        <Flex
                            direction="column"
                            gap="0_5x"
                            {...stylex.props(styles.userMenuTriggerLabel)}
                        >
                            <OverflowTooltip.Root asChild>
                                <div
                                    {...stylex.props(
                                        labelStyles,
                                        styles.secondaryText,
                                    )}
                                >
                                    {label}
                                </div>
                            </OverflowTooltip.Root>
                            <OverflowTooltip.Root asChild>
                                <div
                                    {...stylex.props(
                                        labelStyles,
                                        styles.secondaryText,
                                    )}
                                >
                                    {subLabel}
                                </div>
                            </OverflowTooltip.Root>
                        </Flex>
                        <ChevronUpIcon />
                    </>
                )}
            </button>
        </Flex>
    );
});

UserMenuTrigger.displayName = 'AppNavigation.UserMenuTrigger';

interface AppNavigationUserMenuHeaderProps
    extends React.HTMLAttributes<HTMLDivElement> {
    /**
     * The label of the app navigation user menu header.
     */
    label: string;
    /**
     * The sub label of the app navigation user menu header.
     */
    subLabel: string;
    /**
     * The avatar of the app navigation user menu header.
     */
    avatar?: React.ReactNode | undefined;
}

const UserMenuHeader = forwardRef<
    HTMLDivElement,
    AppNavigationUserMenuHeaderProps
>(function AppNavigationUserMenuHeader(
    { className, style, avatar, label, subLabel, ...props },
    ref,
) {
    const mergedStyles = useMergedStyles(
        className,
        style,
        stylex.props(styles.userMenuHeader),
    );
    const labelStyles = useTypeRamp('label');
    const subLabelStyles = useTypeRamp('smallParagraphBold');

    return (
        <Flex ref={ref} align="center" {...props} {...mergedStyles} asChild>
            <Menu.SectionHeader>
                {avatar}
                <Flex
                    direction="column"
                    gap="0_5x"
                    {...stylex.props(styles.userMenuHeaderLabel)}
                >
                    <OverflowTooltip.Root asChild>
                        <div {...stylex.props(labelStyles)}>{label}</div>
                    </OverflowTooltip.Root>
                    <OverflowTooltip.Root asChild>
                        <div
                            {...stylex.props(
                                subLabelStyles,
                                styles.secondaryText,
                            )}
                        >
                            {subLabel}
                        </div>
                    </OverflowTooltip.Root>
                </Flex>
            </Menu.SectionHeader>
        </Flex>
    );
});

UserMenuHeader.displayName = 'AppNavigation.UserMenuHeader';

export type {
    AppNavigationProps,
    AppNavigationGroupProps,
    AppNavigationLogoProps,
    AppNavigationNavItemProps,
    AppNavigationUserMenuHeaderProps,
    AppNavigationUserMenuTriggerProps,
};

export {
    Root,
    Body,
    NavItem,
    Group,
    Footer,
    UserMenuTrigger,
    UserMenuHeader,
    Logo,
    SnowflakeLogo,
};
