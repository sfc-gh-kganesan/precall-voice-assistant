import { Slottable } from '@radix-ui/react-slot';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import type { IconType } from '@snowflake/stellar-icons';
import { IconContextProvider } from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import { forwardRef, useContext } from 'react';

import type { Size, SlottedContainerProps } from '../main';
import { OverflowTooltip, SlottedContainer } from '../main';
import { TooltipContext } from '../Tooltip/TooltipContext';
import { SizeContext } from '../util/context';

const styles = stylex.create({
    root: {
        alignItems: 'center',
        display: 'inline-flex',
        gap: tokens['space-gap-2xs'],

        backgroundColor: baltoTheme.statusNeutralBackground,
        borderColor: baltoTheme.reusableBorderDefault,
        borderRadius: tokens['radius-xs'],
        borderStyle: 'solid',
        borderWidth: 1,
        color: baltoTheme.reusableTextPrimary,
        fontFamily: baltoTheme.fontFamilyMono,
        padding: `0 ${tokens['space-horizontal-xs']}`,
    },

    small: {
        height: tokens['size-2xs'],

        // These aren't using any defiend values in the type ramp.
        fontSize: '9px',
        lineHeight: '9px',
    },

    regular: {
        height: tokens['size-xs'],

        // These aren't using any defiend values in the type ramp.
        fontSize: '11px',
        lineHeight: '11px',
    },

    label: {
        alignItems: 'center',
        display: 'flex',
        lineHeight: '100%',
        // Web makes text boxes in odd ways that end up making text look offset when centered.
        // There is an upcoming CSS feature that fixes that
        // Until that is available, we need to add a margin to the top of the text to center it.
        marginTop: '1px',
    },
});

interface CodeTagProps extends SlottedContainerProps<'code'> {
    /**
     * The prefix icon of the code tag.
     */
    prefixIcon?: IconType | undefined;
    /**
     * The suffix icon of the code tag.
     */
    suffixIcon?: IconType | undefined;
    /**
     * The size of the code tag.
     * @default "regular"
     */
    size?: Extract<Size, 'small' | 'regular'> | undefined;
}

const CodeTag = forwardRef<HTMLDivElement, CodeTagProps>(
    (
        {
            children,
            size: sizeProp,
            prefixIcon: PrefixIcon,
            suffixIcon: SuffixIcon,
            ...props
        },
        ref,
    ) => {
        const contextSize = useContext(SizeContext);
        const size = sizeProp ?? contextSize ?? 'regular';
        const isTooltipTrigger = useContext(TooltipContext);

        return (
            <IconContextProvider color="currentColor" size={tokens['size-2xs']}>
                <SlottedContainer
                    tag="code"
                    ref={ref}
                    stylexProps={stylex.props(
                        styles.root,
                        size === 'small' && styles.small,
                        size === 'regular' && styles.regular,
                    )}
                    {...props}
                >
                    {PrefixIcon && size === 'regular' && <PrefixIcon />}
                    {isTooltipTrigger ? (
                        <span {...stylex.props(styles.label)}>
                            <Slottable>{children}</Slottable>
                        </span>
                    ) : (
                        <OverflowTooltip.Root asChild>
                            <span {...stylex.props(styles.label)}>
                                <Slottable>{children}</Slottable>
                            </span>
                        </OverflowTooltip.Root>
                    )}
                    {SuffixIcon && size === 'regular' && <SuffixIcon />}
                </SlottedContainer>
            </IconContextProvider>
        );
    },
);

CodeTag.displayName = 'CodeTag';

export type { CodeTagProps };
export { CodeTag };
