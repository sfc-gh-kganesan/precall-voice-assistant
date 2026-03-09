import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import * as stylex from '@stylexjs/stylex';
import type { SVGAttributes } from 'react';
import { forwardRef } from 'react';
import { OverlayArrow } from 'react-aria-components';

import { useMergedStyles } from '../../hooks';

const styles = stylex.create({
    arrow: {
        filter: `drop-shadow(${baltoTheme.elevation_3ShadowOfsetX} ${baltoTheme.elevation_3ShadowOffsetY} ${baltoTheme.elevation_3ShadowBlur} ${baltoTheme.elevation_3ShadowColor})`,

        transform: {
            default: 'translateY(-2px)',
            ":is([data-placement='bottom'] *)":
                'rotate(180deg) translateY(-2px)',
            ":is([data-placement='right'] *)": 'rotate(90deg) translateY(-6px)',
            ":is([data-placement='left'] *)": 'rotate(-90deg) translateY(-6px)',
        },
    },
    arrowStroke: {
        fill: baltoTheme.surfaceLevel_3Border,
    },
    arrowFill: {
        fill: baltoTheme.surfaceLevel_3Background,
    },
    arrowContainer: {
        alignItems: 'center',
        display: 'flex',
        justifyContent: 'center',
    },
});

const Arrow = forwardRef<SVGSVGElement, SVGAttributes<SVGElement>>(
    function Arrow({ className, style, ...props }, ref) {
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.arrow),
        );
        return (
            <OverlayArrow {...stylex.props(styles.arrowContainer)}>
                <svg
                    {...props}
                    width="18"
                    height="9"
                    viewBox="0 0 18 9"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                    {...styleProps}
                    ref={ref}
                >
                    <path
                        d="M9.00001 9L0 1.74864e-06L9.00001 0L18 1.58716e-07L9.00001 9Z"
                        {...stylex.props(styles.arrowFill)}
                    />
                    <path
                        fillRule="evenodd"
                        clipRule="evenodd"
                        d="M17 1L9.00001 9L1 1H2.41421L9.00001 7.58579L15.5858 1L17 1Z"
                        {...stylex.props(styles.arrowStroke)}
                    />
                </svg>
            </OverlayArrow>
        );
    },
);

export { Arrow };
