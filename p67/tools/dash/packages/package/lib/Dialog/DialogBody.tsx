import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';
import { Flex } from '../Layout';
import { devError } from '../util/dev-warning';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { useDialogContext } from './DialogContext';

type DialogBodyProps<T extends keyof ReactHTML = 'div'> =
    SlottedContainerProps<T>;

const styles = stylex.create({
    body: {
        overflow: 'auto',
        padding: `0 ${tokens['space-horizontal-3xl']} ${tokens['space-vertical-2xl']}` /* 0 32 */,
    },
    fullscreenBody: { flexGrow: 1, minHeight: 0 },
});

/**
 * The body component for the Dialog component.
 */
const DialogBody = forwardRef<HTMLDivElement, DialogBodyProps>(
    (props, forwardedRef) => {
        const { isInDialog, isFullscreenDialog } =
            useDialogContext('DialogBody');
        if (!isInDialog) {
            devError('Dialog.Body cannot be used outside of Dialog.');
        }
        return (
            <Flex
                direction="column"
                {...props}
                {...stylex.props(
                    styles.body,
                    isFullscreenDialog && styles.fullscreenBody,
                )}
                ref={forwardedRef}
            />
        );
    },
);

DialogBody.displayName = 'Dialog.Body';
export type { DialogBodyProps };
export { DialogBody };
