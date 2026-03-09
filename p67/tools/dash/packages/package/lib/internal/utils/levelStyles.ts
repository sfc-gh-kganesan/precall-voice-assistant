import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';

const levelStyles = stylex.create({
    level3Surface: {
        backgroundColor: baltoTheme.surfaceLevel_3Background,
        borderColor: baltoTheme.surfaceLevel_3Border,
        borderStyle: 'solid',
        borderWidth: 1,
        borderRadius: `${tokens['radius-md']}`,
        boxShadow: `${baltoTheme.elevation_3ShadowOfsetX} ${baltoTheme.elevation_3ShadowOffsetY} ${baltoTheme.elevation_3ShadowBlur} ${baltoTheme.elevation_3ShadowColor}`,
    },
});

export { levelStyles };
