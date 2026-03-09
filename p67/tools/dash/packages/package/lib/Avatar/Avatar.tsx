import { useLayoutEffect } from '@react-aria/utils';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type React from 'react';
import { forwardRef, useContext, useState } from 'react';
import { mergeProps } from 'react-aria';

import { useMergedStyles } from '../hooks';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import type { Size } from '../types';
import { SizeContext } from '../util/context';

const styles = stylex.create({
    root: {
        alignItems: 'center',
        display: 'inline-flex',
        flexShrink: 0,
        justifyContent: 'center',

        backgroundColor: baltoTheme.surfaceLevel_2Background,
        borderColor: baltoTheme.surfaceLevel_2Border,
        borderRadius: '100%',
        borderStyle: 'solid',
        borderWidth: 1,
        overflow: 'hidden',
        userSelect: 'none',
        verticalAlign: 'middle',
    },

    small: {
        height: tokens['size-sm'],
        width: tokens['size-sm'],
    },
    regular: {
        height: tokens['size-md'],
        width: tokens['size-md'],
    },

    image: {
        height: '100%',
        width: '100%',
    },

    fallback: {
        alignItems: 'center',
        display: 'inline-flex',
        justifyContent: 'center',
        textTransform: 'uppercase',

        borderRadius: 'inherit',
        color: baltoTheme.reusableTextPrimary,
        height: '100%',
        objectFit: 'cover',
        objectPosition: 'center',
        width: '100%',
    },
});

/**
 * Shown when the image fails to load.
 */
function Fallback({
    size,
    className,
    style,
    ...props
}: React.ComponentProps<'span'> & Pick<AvatarProps, 'size'>) {
    const fallbackTextStyles = useTypeRamp(
        size === 'small' ? 'smallParagraph' : 'paragraph',
    );
    const mergedStyles = useMergedStyles(
        className,
        style,
        stylex.props(styles.fallback, fallbackTextStyles),
    );

    return <span {...mergedStyles} {...props} />;
}

interface AvatarProps extends React.HTMLAttributes<HTMLSpanElement> {
    /**
     * The image to display in the avatar.
     */
    image?: string | undefined;
    /**
     * The name to display in the avatar. Used as an aria label.
     */
    name: string;
    /**
     * Override the initials to display in the avatar fallback.
     */
    initials?: string | undefined;
    /**
     * The size of the avatar.
     * @default "regular"
     */
    size?: Extract<Size, 'small' | 'regular'> | undefined;
}

type ImageLoadingStatus = 'loading' | 'loaded' | 'fallback';

const Avatar = forwardRef<HTMLSpanElement, AvatarProps>(function Avatar(
    { image, name, initials, size: sizeProp, className, style, ...props },
    ref,
) {
    const contextSize = useContext(SizeContext);
    const size = sizeProp ?? contextSize ?? 'regular';
    const mergedStyles = useMergedStyles(
        className,
        style,
        stylex.props(
            styles.root,
            size === 'small' && styles.small,
            size === 'regular' && styles.regular,
        ),
    );

    const [loadingStatus, setLoadingStatus] = useState<ImageLoadingStatus>(
        image ? 'loading' : 'fallback',
    );

    useLayoutEffect(() => {
        if (!image) return;

        const img = new Image();
        const handleLoad = () => setLoadingStatus('loaded');
        const handleError = () => setLoadingStatus('fallback');

        img.addEventListener('load', handleLoad);
        img.addEventListener('error', handleError);

        img.src = image;

        return () => {
            img.removeEventListener('load', handleLoad);
            img.removeEventListener('error', handleError);
        };
    }, [image]);

    return (
        <span {...mergeProps(props, mergedStyles)} ref={ref}>
            {loadingStatus === 'loaded' ? (
                <img src={image} alt={name} {...stylex.props(styles.image)} />
            ) : loadingStatus === 'fallback' ? (
                <Fallback size={size}>{initials ?? name.charAt(0)}</Fallback>
            ) : null}
        </span>
    );
});

Avatar.displayName = 'Avatar';

export type { AvatarProps };
export { Avatar };
