import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';

const styles = stylex.create({
    checkbox: {
        backgroundColor: {
            ":is([data-state='unchecked'])":
                baltoTheme.componentFormControlBackgroundDefault,
            ":is([data-state='unchecked'][data-disabled])":
                baltoTheme.componentFormControlBackgroundDisabled,

            ":is([data-state='checked'],[data-state='indeterminate']):is([data-disabled])":
                baltoTheme.componentFormControlBackgroundSelectedDisabled,
            ":is([data-state='checked'],[data-state='indeterminate']):not([data-disabled])":
                baltoTheme.componentFormControlBackgroundSelectedDefault,
            ":is([data-state='checked'],[data-state='indeterminate']):not([data-disabled]):hover":
                baltoTheme.componentFormControlBackgroundSelectedHover,
        },
        borderColor: {
            ":is([data-state='unchecked']):is([data-disabled])":
                baltoTheme.componentFormControlBorderDisabled,
            ":is([data-state='unchecked']):not([data-disabled])":
                baltoTheme.componentFormControlBorderDefault,
            ":is([data-state='unchecked']):not([data-disabled]):hover":
                baltoTheme.componentFormControlBorderHover,
            ":is([data-state='unchecked']):not([data-disabled]):focus":
                baltoTheme.componentFormControlBorderActive,
        },
        borderRadius: tokens['radius-xs'] /* 6 */,
        borderStyle: 'solid',
        borderWidth: {
            default: 1,
            ":is([data-state='checked'],[data-state='indeterminate'])": 0,
        },
        color: {
            ":is([data-state='checked'],[data-state='indeterminate'])":
                baltoTheme.componentFormControlKnobDefault,
            ":is([data-state='checked'],[data-state='indeterminate']):is([data-disabled])":
                baltoTheme.componentFormControlKnobSelectedDisabled,
        },
        cursor: {
            default: 'pointer',
            ':is([data-disabled])': 'not-allowed',
        },
        display: 'inline-block',
        flexShrink: 0,
        height: tokens['size-2xs'],
        margin: 0,
        outline: {
            default: 'none',
            ':not([data-disabled]):focus': `2px solid ${baltoTheme.reusableBorderFocusedActiveItem}`,
        },
        padding: 0,
        width: tokens['size-2xs'],
    },
});

/**
 *
 */
function useCheckboxStyles() {
    return styles.checkbox;
}

export { useCheckboxStyles };
