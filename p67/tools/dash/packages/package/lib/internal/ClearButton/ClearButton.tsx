import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import {
    ErrorCircleFillIcon,
    IconContextProvider,
} from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';

import { useMergedStyles } from '../../hooks';

const styles = stylex.create({
    icon: {
        alignItems: 'center',
        backgroundColor: {
            default: 'transparent',
            ':hover': baltoTheme.statusNeutralBackground,
            ':active': baltoTheme.statusNeutralBackground,
        },
        borderRadius: tokens['radius-sm'],
        borderWidth: 0,
        color: baltoTheme.reusableIconDefault,
        cursor: 'pointer',
        display: 'flex',
        justifyContent: 'center',
        padding: 0,
        zIndex: 1,
    },
});

/**
 * A button that clears the input.
 */
export function ClearButton({
    className,
    style,
    disabled,
    onClick,
    onPointerDown,
    ...props
}: Omit<React.ComponentPropsWithoutRef<'button'>, 'children'>) {
    const mergedStyles = useMergedStyles(
        className,
        style,
        stylex.props(styles.icon),
    );
    const disabledFunction = (e: React.MouseEvent<HTMLButtonElement>) => {
        e.preventDefault();
        e.stopPropagation();
    };

    return (
        <button
            type="button"
            aria-label="Clear input"
            {...mergedStyles}
            {...props}
            aria-disabled={disabled}
            onPointerDown={disabled ? disabledFunction : onPointerDown}
            onClick={disabled ? disabledFunction : onClick}
        >
            <IconContextProvider>
                <ErrorCircleFillIcon />
            </IconContextProvider>
        </button>
    );
}
