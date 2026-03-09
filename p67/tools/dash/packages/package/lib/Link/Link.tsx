import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import * as stylex from '@stylexjs/stylex';
import { forwardRef, useContext, useMemo } from 'react';
import { mergeProps } from 'react-aria';

import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { StatusContext } from '../Status/internal/StatusContext';
import { useStatusLinkColors } from '../Status/internal/useStatusColors';
import type { ParagraphContextValue } from '../Text/internal/ParagraphContext';
import { ParagraphContext } from '../Text/internal/ParagraphContext';
import { useParagraphStyles } from '../Text/internal/useParagraphStyles';
import type { SlottedAnchorContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';

interface LinkProps extends SlottedAnchorContainerProps {
    /**
     * Whether the link is disabled.
     * @default false
     */
    disabled?: boolean | undefined;
    /**
     * Whether the link is external.
     * This will open the link in a new tab.
     * @default false
     */
    isExternal?: boolean | undefined;
}
const styles = stylex.create({
    link: {
        cursor: 'pointer',
        textDecoration: 'underline',
    },
    default: {
        color: {
            default: baltoTheme.reusableLinkDefault,
            ':hover': baltoTheme.reusableLinkHover,
            ':active': baltoTheme.reusableLinkPress,
        },
    },
    defaultDisabled: {
        color: baltoTheme.reusableLinkDisabled,
        cursor: 'not-allowed',
    },
});

const Link = forwardRef<HTMLAnchorElement, LinkProps>((props, forwardedRef) => {
    const { disabled, isExternal, ...otherProps } = props;
    const ctx = useContext(StatusContext);
    const statusLinkStyles = useStatusLinkColors(ctx?.variant, disabled);
    const parentParagraphContext = useContext(ParagraphContext);
    const spanContext = useMemo(
        (): ParagraphContextValue => ({
            bold: parentParagraphContext?.bold ?? false,
            small: parentParagraphContext?.small ?? false,
            variant: parentParagraphContext?.variant ?? 'primary',
            caps: parentParagraphContext?.caps ?? false,
        }),
        [parentParagraphContext],
    );
    const paragraphStyles = useParagraphStyles(spanContext);
    const textStyles = useTypeRamp('link');

    return (
        <SlottedContainer
            {...mergeProps(otherProps, {
                target: isExternal ? '_blank' : undefined,
                rel: isExternal ? 'noopener noreferrer' : undefined,
                onClick: (event: React.MouseEvent) => {
                    if (disabled) {
                        event.preventDefault();
                    }
                },
            })}
            tag="a"
            aria-disabled={disabled ? true : undefined}
            stylexProps={stylex.props(
                textStyles,
                styles.link,
                disabled ? styles.defaultDisabled : styles.default,
                statusLinkStyles,
                ...(parentParagraphContext ? paragraphStyles : []),
            )}
            ref={forwardedRef}
        />
    );
});

Link.displayName = 'Link';
export type { LinkProps };
export { Link };
