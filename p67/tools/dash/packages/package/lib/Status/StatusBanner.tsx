import { Slottable } from '@radix-ui/react-slot';
import { ClearIcon } from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactNode } from 'react';
import { forwardRef } from 'react';
import translations from '../../translations/base.json';
import { IconButton } from '../Button';
import { useMergedStyles } from '../hooks';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { Flex } from '../Layout';
import {
    HeadingContext,
    useCreateHeadingContext,
} from '../Text/internal/HeadingContext';
import { useHeadingTag } from '../Text/internal/useHeadingTag';
import type { StatusContainerProps } from './internal/StatusContainer';
import { StatusContainer } from './internal/StatusContainer';
import { StatusIcon } from './internal/StatusIcon';
import { useStatusTextColors } from './internal/useStatusColors';
import type { StatusVariant } from './types';

interface StatusBannerProps
    extends Omit<StatusContainerProps<'div'>, 'tag' | 'variant'> {
    /**
     * The heading of the status banner.
     */
    heading: string;
    /**
     * The description of the status banner.
     */
    description?: string | undefined;
    /**
     * The variant of the status banner.
     * @default "neutral"
     */
    variant?: StatusVariant | undefined;
    /**
     * The cta button of the status banner.
     */
    action?: ReactNode | undefined;
    /**
     * A function to call when the status banner is dismissed.
     */
    onClose?: (() => void) | undefined;
}

const styles = stylex.create({
    base: {
        borderRadius: tokens['radius-md'] /* 4 */,
        containerType: 'inline-size',
        minWidth: tokens['size-2xl'],
    },
    heading: {
        // TODO: this design seemingly uses the old type ramp.
        lineHeight: '16px',
        margin: 0,
        padding: 0,
    },
    statusIcon: {
        flexShrink: 0,
        marginBlockStart: tokens['space-vertical-lg'],
        marginInlineStart: tokens['space-horizontal-lg'],
    },
    actionAlignment: {
        flexDirection: 'row',
        flexGrow: 1,
        marginBlockEnd: tokens['space-vertical-lg'],
        marginBlockStart: tokens['space-vertical-lg'],
        marginInlineEnd: tokens['space-horizontal-lg'],
        minWidth: 0,
    },
    actionAlignmentNarrow: {
        flexDirection: {
            default: 'row',
            '@container (width <= 480px)': 'column',
        },
    },
    action: {
        alignSelf: {
            default: 'center',
            '@container (width <= 480px)': 'flex-start',
        },
        marginInlineEnd: {
            ':last-child': tokens['space-horizontal-lg'],
        },
    },
    description: {
        margin: 0,
        maxWidth: '80em',
        padding: 0,
    },
});

const StatusBannerHeading = (props: {
    /**
     * The children of the status banner heading.
     */
    children: ReactNode;
    /**
     * The variant of the status banner heading.
     */
    variant: StatusVariant;
}) => {
    const { children, variant } = props;
    const { tag: HeadingTag } = useHeadingTag();
    const stylexTextProps = useStatusTextColors(variant);
    const headingTextStyles = useTypeRamp('label');
    return (
        <HeadingTag
            {...stylex.props(
                headingTextStyles,
                styles.heading,
                stylexTextProps,
            )}
        >
            {children}
        </HeadingTag>
    );
};
const StatusBanner = forwardRef<HTMLDivElement, StatusBannerProps>(
    (props, forwardedRef) => {
        const {
            heading,
            description,
            children,
            className,
            style,
            onClose,
            variant = 'neutral',
            action,
            ...otherProps
        } = props;

        const headingContext = useCreateHeadingContext();
        const descriptionStyles = useTypeRamp('smallParagraph');
        const stylexTextProps = useStatusTextColors(variant);
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.base),
        );

        return (
            <HeadingContext.Provider value={headingContext}>
                <Flex direction="row" align="start" grow={1} asChild>
                    <StatusContainer
                        {...otherProps}
                        tag={'section'}
                        role="status"
                        ref={forwardedRef}
                        variant={variant}
                        {...styleProps}
                    >
                        <StatusIcon {...stylex.props(styles.statusIcon)} />
                        <Flex
                            {...stylex.props(
                                styles.actionAlignment,
                                action ? styles.actionAlignmentNarrow : null,
                            )}
                        >
                            <Flex direction="column" gap="0_5x" grow={1}>
                                <StatusBannerHeading variant={variant}>
                                    {heading}
                                </StatusBannerHeading>
                                {!!description && (
                                    <p
                                        {...stylex.props(
                                            descriptionStyles,
                                            stylexTextProps,
                                            styles.description,
                                        )}
                                    >
                                        {description}
                                    </p>
                                )}
                                <Slottable>{children}</Slottable>
                            </Flex>

                            {(action || onClose) && (
                                <Flex align="center" gap="0_75x">
                                    {action && (
                                        <Flex {...stylex.props(styles.action)}>
                                            {action}
                                        </Flex>
                                    )}
                                    {onClose && (
                                        <IconButton
                                            aria-label={
                                                translations.en['StatusBanner']
                                                    .dismiss
                                            }
                                            icon={ClearIcon}
                                            variant="tertiary"
                                            onClick={onClose}
                                        />
                                    )}
                                </Flex>
                            )}
                        </Flex>
                    </StatusContainer>
                </Flex>
            </HeadingContext.Provider>
        );
    },
);

StatusBanner.displayName = 'StatusBanner';

export type { StatusBannerProps };
export { StatusBanner };
