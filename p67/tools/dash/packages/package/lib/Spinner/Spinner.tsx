import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { baseDimension } from '@snowflake/balto-themes/baseDimension.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef, useContext } from 'react';

import translations from '../../translations/base.json';
import type { Size } from '../types';
import { SizeContext } from '../util/context';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';

interface SpinnerProps<T extends keyof ReactHTML = 'div'>
    extends SlottedContainerProps<T> {
    /**
     * The size of the spinner.
     * @default "regular"
     */
    size?: Extract<Size, 'small' | 'regular'> | undefined;
}

const rotate = stylex.keyframes({
    from: { transform: 'rotate(50deg)' },
    to: { transform: 'rotate(410deg)' },
});
const styles = stylex.create({
    spinner: {
        animationDelay: '0s',
        animationDuration: '0.75s',
        animationFillMode: 'forwards',
        animationIterationCount: 'infinite',
        animationName: rotate,
        animationPlayState: 'running',
        animationTimingFunction: 'cubic-bezier(0.4, 0.15, 0.6, 0.85)',
        borderColor: baltoTheme.reusableBorderDisabled,
        borderLeftColor: baltoTheme.reusableIconDefault,
        borderRadius: '50%',
        borderStyle: 'solid',
    },
    small: {
        borderWidth: baseDimension.spacing_0_25x /* 2 */,
        height: tokens['size-2xs'] /* 16 */,
        width: tokens['size-2xs'] /* 16 */,
    },
    regular: {
        borderWidth: tokens['size-6xs'] /* 4 */,
        height: tokens['size-xl'] /* 48 */,
        width: tokens['size-xl'] /* 48 */,
    },
});

const Spinner = forwardRef<HTMLDivElement, SpinnerProps>(
    (props, forwardedRef) => {
        const contextSize = useContext(SizeContext);
        const { size = contextSize, ...otherProps } = props;
        const stylexProps = stylex.props(
            styles.spinner,
            size === 'small' ? styles.small : styles.regular,
        );
        return (
            <SlottedContainer
                {...otherProps}
                tag="div"
                ref={forwardedRef}
                stylexProps={stylexProps}
                aria-busy="true"
                role="progressbar"
                aria-label={translations.en['loading-indicator'].label}
                aria-valuetext={translations.en['loading-indicator'].label}
            />
        );
    },
);
Spinner.displayName = 'Spinner';
export type { SpinnerProps };
export { Spinner };
