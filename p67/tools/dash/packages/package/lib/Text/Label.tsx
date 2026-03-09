import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { IconContextProvider } from '@snowflake/stellar-icons';
import * as stylex from '@stylexjs/stylex';
import { forwardRef, useContext } from 'react';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import type { Size } from '../types';
import { SizeContext } from '../util/context';
import type { SlottedLabelContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';
import type { TextVariant } from './types';

interface LabelProps extends SlottedLabelContainerProps {
    /**
     * The variant of the label.
     */
    variant?: TextVariant | undefined;
    /**
     * The size of the label.
     * @default "regular"
     */
    size?: Extract<Size, 'small' | 'regular'> | undefined;
    /**
     * Whether the label is in all caps.
     * @default false
     */
    caps?: boolean | undefined;
}

const styles = stylex.create({
    label: {
        margin: 0,
        padding: 0,
    },
    primary: {
        color: baltoTheme.reusableTextPrimary,
    },
    secondary: {
        color: baltoTheme.reusableTextSecondary,
    },
    caution: {
        color: baltoTheme.statusCautionMessageText,
    },
    critical: {
        color: baltoTheme.statusCriticalMessageText,
    },
});

const Label = forwardRef<HTMLLabelElement, LabelProps>(
    (props, forwardedRef) => {
        const contextSize = useContext(SizeContext);
        const { size = contextSize, variant, caps, ...otherProps } = props;
        const textStyles = useTypeRamp(
            caps
                ? size === 'small'
                    ? 'allCapsSmall'
                    : 'allCaps'
                : size === 'small'
                  ? 'labelSmall'
                  : 'label',
        );
        return (
            <IconContextProvider>
                <SlottedContainer
                    {...otherProps}
                    tag={'label'}
                    stylexProps={stylex.props(
                        textStyles,
                        styles.label,
                        variant === 'primary' && styles.primary,
                        variant === 'secondary' && styles.secondary,
                        variant === 'caution' && styles.caution,
                        variant === 'critical' && styles.critical,
                    )}
                    ref={forwardedRef}
                />
            </IconContextProvider>
        );
    },
);

Label.displayName = 'Label';
export type { LabelProps };
export { Label };
