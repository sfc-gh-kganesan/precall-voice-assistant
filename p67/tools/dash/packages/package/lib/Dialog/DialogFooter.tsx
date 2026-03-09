import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML, ReactNode } from 'react';
import { forwardRef } from 'react';
import { Flex } from '../Layout';
import { devError } from '../util/dev-warning';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { useDialogContext } from './DialogContext';

interface DialogFooterProps<T extends keyof ReactHTML = 'div'>
    extends SlottedContainerProps<T> {
    /**
     * The primary CTA area of the dialog footer.
     */
    primaryCtaArea: ReactNode;
    /**
     * The secondary CTA area of the dialog footer.
     */
    secondaryCtaArea?: ReactNode | undefined;
    /**
     * The children of the dialog footer.
     */
    children?: never | undefined;
}

const styles = stylex.create({
    footer: {
        borderTopColor: baltoTheme.reusableBorderDefault,
        borderTopStyle: 'solid',
        borderTopWidth: 1,
        padding: `${tokens['space-vertical-lg']} ${tokens['space-horizontal-2xl']}` /* 16 24 */,
    },
});

/**
 * The footer component for the Dialog component.
 */
const DialogFooter = forwardRef<HTMLDivElement, DialogFooterProps>(
    (props, forwardedRef) => {
        const { isInDialog } = useDialogContext('DialogFooter');

        if (!isInDialog) {
            devError('Dialog.Footer cannot be used outside of Dialog.');
        }

        const { primaryCtaArea, secondaryCtaArea, ...otherProps } = props;

        return (
            <Flex
                justify="between"
                {...otherProps}
                {...stylex.props(styles.footer)}
                ref={forwardedRef}
            >
                <Flex>{secondaryCtaArea && secondaryCtaArea}</Flex>
                <Flex gap="1x" align="end">
                    {primaryCtaArea}
                </Flex>
            </Flex>
        );
    },
);

DialogFooter.displayName = 'Dialog.Footer';
export type { DialogFooterProps };
export { DialogFooter };
