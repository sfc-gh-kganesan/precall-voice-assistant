import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';

const cardStyles = stylex.create({
    default: {
        backgroundColor: baltoTheme.surfaceLevel_2Background,
        borderColor: baltoTheme.surfaceLevel_2Border,
        borderStyle: 'solid',
        borderWidth: 1,
        borderRadius: tokens['radius-md'],
        margin: 0,
        minWidth: 0, // Allow Card to shrink to fit a Flex container and show ellipsis on heading.
        padding: tokens['space-vertical-2xl'],
        textAlign: 'start',
    },
    selectable: {
        transition:
            'box-shadow 200ms linear, background-color 200ms linear, border-color 200ms linear',
        width: '100%',
        cursor: 'pointer',
        boxShadow: {
            default: 'none',
            ':hover': baltoTheme.elevation_2BoxShadow,
        },
        backgroundColor: {
            default: baltoTheme.surfaceLevel_2Background,
            ':hover': baltoTheme.surfaceLevel_3Background,
        },
        borderColor: {
            default: baltoTheme.surfaceLevel_2Border,
            ':hover': baltoTheme.surfaceLevel_3Border,
        },
    },
    selected: {
        borderWidth: 0,
        borderStyle: 'none',
        outline: `2px solid ${baltoTheme.reusableBorderActive}`,
    },
});

const dataCardStyles = stylex.create({
    default: {
        rowGap: tokens['space-gap-sm'],
    },
    small: {
        padding: tokens['space-vertical-lg'],
    },
});

export { cardStyles, dataCardStyles };
