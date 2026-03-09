import { createContext } from '@radix-ui/react-context';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { IconContextProvider } from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type React from 'react';
import type { HTMLAttributes } from 'react';
import { forwardRef } from 'react';

import { useMergedStyles } from '../hooks';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { Flex } from '../Layout';
import { Paragraph } from '../Text';

type EmptyStateVariant = 'actionable' | 'non-actionable';

const [EmptyStateContext, useEmptyStateContext] = createContext<{
    /**
     * The variant of the empty state.
     */
    variant: EmptyStateVariant;
}>('EmptyState');

const styles = stylex.create({
    root: {
        height: '100%',
        width: '100%',
    },
    rootContent: {
        maxWidth: 320,
    },
    illustration: {
        marginBottom: tokens['space-vertical-3xl'],
    },
    icon: {
        marginBottom: tokens['space-vertical-lg'],
    },
    body: {
        marginTop: tokens['space-vertical-lg'],
        textAlign: 'center',
    },
    footer: {
        marginTop: tokens['space-vertical-2xl'],
    },
    header: {
        color: baltoTheme.reusableTextHeader,
        margin: 0,
        padding: 0,
        textAlign: 'center',
        textWrap: 'balance',
    },
    nonActionableSubHeader: {
        color: baltoTheme.reusableTextSecondary,
    },
});

interface EmptyStateProps extends HTMLAttributes<HTMLDivElement> {
    /**
     * The variant of the empty state.
     */
    variant?: EmptyStateVariant | undefined;
}

const EmptyStateRoot = forwardRef<HTMLDivElement, EmptyStateProps>(
    ({ variant = 'actionable', className, style, children, ...props }, ref) => {
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.root),
        );

        return (
            <EmptyStateContext variant={variant}>
                <Flex
                    align="center"
                    justify="center"
                    direction="column"
                    ref={ref}
                    {...props}
                    {...styleProps}
                >
                    <Flex
                        direction="column"
                        gap="0x"
                        align="center"
                        {...stylex.props(styles.rootContent)}
                    >
                        {children}
                    </Flex>
                </Flex>
            </EmptyStateContext>
        );
    },
);

EmptyStateRoot.displayName = 'EmptyState.Root';

const Pictogram = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
    ({ className, style, ...props }, ref) => {
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.icon),
        );

        return (
            <IconContextProvider
                color={baltoTheme.reusableIconSubtle}
                size={tokens['size-xl']}
            >
                <div data-image ref={ref} {...props} {...styleProps} />
            </IconContextProvider>
        );
    },
);

Pictogram.displayName = 'EmptyState.Pictogram';

const Illustration = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
    ({ className, style, ...props }, ref) => {
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.illustration),
        );
        return <div data-image ref={ref} {...props} {...styleProps} />;
    },
);

Illustration.displayName = 'EmptyState.Illustration';

const Title = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
    ({ className, style, ...props }, ref) => {
        const { variant } = useEmptyStateContext('EmptyStateTitle');
        const textStyles = useTypeRamp('subHeader');
        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(
                textStyles,
                styles.header,
                variant === 'non-actionable' && styles.nonActionableSubHeader,
            ),
        );

        return (
            <div
                ref={ref}
                data-title
                {...(props as React.HTMLAttributes<HTMLHeadingElement>)}
                {...mergedStyles}
            />
        );
    },
);

Title.displayName = 'EmptyState.Title';

const Body = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
    ({ className, style, children, ...props }, ref) => {
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.body),
        );
        return (
            <Paragraph
                variant="secondary"
                ref={ref}
                {...props}
                {...styleProps}
                asChild={true}
            >
                <div>{children}</div>
            </Paragraph>
        );
    },
);

Body.displayName = 'EmptyState.Body';

interface FooterProps extends Omit<HTMLAttributes<HTMLDivElement>, 'children'> {
    /**
     * The secondary action of the empty state footer.
     */
    secondaryAction?: React.ReactNode | undefined;
    /**
     * The primary action of the empty state footer.
     */
    primaryAction?: React.ReactNode | undefined;
}

const Footer = forwardRef<HTMLDivElement, FooterProps>(
    ({ className, style, secondaryAction, primaryAction, ...props }, ref) => {
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.footer),
        );

        return (
            <Flex data-footer ref={ref} {...props} {...styleProps}>
                {secondaryAction}
                {primaryAction}
            </Flex>
        );
    },
);

Footer.displayName = 'EmptyState.Footer';

export { EmptyStateRoot as Root, Pictogram, Illustration, Title, Body, Footer };
