import { Slot } from '@radix-ui/react-slot';
import { baseTheme } from '@snowflake/stellar-tokens/themes/base.stylex';
import { compactTheme } from '@snowflake/stellar-tokens/themes/compact.stylex';
import * as stylex from '@stylexjs/stylex';
import { createContext } from 'react';

import type { Size } from '../types';

const SizeContext = createContext<
    Extract<Size, 'small' | 'regular'> | undefined
>(undefined);

// @ts-expect-error - Provider is not typed
SizeContext.Provider.displayName = 'SizeContext.Provider';

interface SizeProviderProps {
    /**
     * The children of the density provider.
     */
    children: React.ReactNode;
    /**
     * The density of the density provider.
     */
    density: 'compact' | 'regular';
    /**
     * Whether to spread the density overrides on the first (only) child of the density provider.
     */
    asChild?: boolean | undefined;
}

/**
 * A wrapper component that overrides the density tokens for the children.
 */
function DensityProvider({
    children,
    density = 'regular',
    asChild = false,
}: SizeProviderProps) {
    const Component = asChild ? Slot : 'div';

    return (
        <Component
            {...stylex.props(
                density === 'compact' && compactTheme,
                density === 'regular' && baseTheme,
            )}
        >
            {children}
        </Component>
    );
}

export { DensityProvider, SizeContext };
