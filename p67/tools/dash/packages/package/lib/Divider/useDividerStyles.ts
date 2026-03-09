import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import * as stylex from '@stylexjs/stylex';

const styles = stylex.create({
    divider: {
        borderWidth: 0,
        margin: 0,
        padding: 0,
    },
    horizontal: {
        borderBottomColor: baltoTheme.reusableBorderDefault,
        borderBottomStyle: 'solid',
        borderBottomWidth: 1,
        width: '100%',
    },
    vertical: {
        borderLeftColor: baltoTheme.reusableBorderDefault,
        borderLeftStyle: 'solid',
        borderLeftWidth: 1,
        height: '100%',
    },
});

export const useDividerStyles = ({
    direction,
}: {
    direction: 'horizontal' | 'vertical';
}) => {
    return [
        styles.divider,
        direction === 'horizontal' && styles.horizontal,
        direction === 'vertical' && styles.vertical,
    ];
};
