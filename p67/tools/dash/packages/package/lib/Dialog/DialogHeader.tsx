import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';
import { Heading as HeadingPrimitive } from 'react-aria-components';

import type { IllustrationType } from '../internal';
import { BadgeIllustration } from '../internal';
import { Flex } from '../Layout';
import { Heading, Paragraph } from '../Text';
import { devError, devWarning } from '../util/dev-warning';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { useDialogContext } from './DialogContext';

interface DialogHeaderProps<T extends keyof ReactHTML = 'div'>
    extends SlottedContainerProps<T> {
    /**
     * The heading of the dialog header.
     */
    heading: React.ReactNode;
    /**
     * The sub heading of the dialog header.
     */
    subHeading?: React.ReactNode | undefined;
    /**
     * The badge icon of the dialog header.
     */
    badgeIcon?: IllustrationType | undefined;
    /**
     * The children of the dialog header.
     */
    children?: never | undefined;
}

const styles = stylex.create({
    header: {
        overflow: 'hidden',
        padding: `${tokens['space-vertical-3xl']} ${tokens['space-horizontal-3xl']} ${tokens['space-vertical-2xl']}` /* 32 32 */,
    },
    badgeIcon: {
        marginBlockEnd: tokens['space-vertical-xl'],
    },
    heading: {
        flexShrink: '0',
        overflow: 'hidden',
        textAlign: 'center',
        textOverflow: 'ellipsis',
        width: '100%',
    },
    subHeading: {
        flexShrink: '0',
        overflow: 'hidden',
        textAlign: 'center',
        textOverflow: 'ellipsis',
        width: '100%',
    },
});

/**
 * The header component for the Dialog component.
 */
const DialogHeader = forwardRef<HTMLDivElement, DialogHeaderProps>(
    (props, forwardedRef) => {
        const { isInDialog, ariaDescribedBy } =
            useDialogContext('DialogHeader');

        if (!isInDialog) {
            devError('Dialog.Header cannot be used outside of Dialog.');
        }

        const { heading, subHeading, badgeIcon, ...otherProps } = props;

        if (!subHeading && !ariaDescribedBy) {
            devWarning(
                'Dialog.Header should either use subHeading prop or aria-describedby on the Dialog component to describe the dialog.',
            );
        }

        return (
            <Flex
                direction="column"
                align="center"
                gap="0_5x"
                shrink={0}
                {...otherProps}
                {...stylex.props(styles.header)}
                ref={forwardedRef}
            >
                {badgeIcon && (
                    <BadgeIllustration
                        variant={badgeIcon}
                        size="large"
                        {...stylex.props(styles.badgeIcon)}
                    />
                )}
                <Heading
                    size="subHeader"
                    asChild
                    {...stylex.props(styles.heading)}
                >
                    <HeadingPrimitive slot="title">{heading}</HeadingPrimitive>
                </Heading>
                {subHeading && (
                    <Paragraph
                        variant="secondary"
                        {...stylex.props(styles.subHeading)}
                    >
                        {subHeading}
                    </Paragraph>
                )}
            </Flex>
        );
    },
);

DialogHeader.displayName = 'Dialog.Header';
export type { DialogHeaderProps };
export { DialogHeader };
