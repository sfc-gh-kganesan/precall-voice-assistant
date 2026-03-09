import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';

const menuStyles = stylex.create({
    menuPopover: {
        minWidth: 'max-content',
        overflow: 'auto',
        pointerEvents: 'auto',
    },
    menuContainer: {
        maxWidth: `min(600px, calc(100vw - ${tokens['size-2xs']}))`,
        padding: `${tokens['space-vertical-sm']} 0`,
        outline: 'none',
    },
    menuContainerMatchTriggerWidth: {
        width: `var(--trigger-width)`,
    },
    menuContainerMaxListWidth: (width: string | number) => ({
        maxWidth: width,
    }),
});

export { menuStyles };
