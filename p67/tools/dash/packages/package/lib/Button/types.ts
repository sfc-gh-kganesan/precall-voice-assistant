import type { IconType } from '@snowflake/stellar-icons';

import type { Size } from '../types';
import type { SlottedButtonContainerProps } from '../util/SlottedContainer';

export const buttonVariants = [
    'primary',
    'secondary',
    'tertiary',
    'primary-critical',
] as const;
export type ButtonVariant = (typeof buttonVariants)[number];

export type ButtonSize = Extract<Size, 'small' | 'regular'>;

export interface ButtonProps extends SlottedButtonContainerProps {
    variant?: ButtonVariant | undefined;
    size?: ButtonSize | undefined;
    disabled?: boolean | undefined;
    selected?: boolean | undefined;
    prefixIcon?: IconType | undefined;
    suffixIcon?: IconType | undefined;
    fullWidth?: boolean | undefined;
    isLoading?: boolean | undefined;
}
