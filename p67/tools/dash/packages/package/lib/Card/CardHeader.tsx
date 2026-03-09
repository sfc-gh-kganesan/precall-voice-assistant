import { Slottable } from '@radix-ui/react-slot';
import { InfoCircleIcon } from '@snowflake/stellar-icons';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML, ReactNode } from 'react';
import { forwardRef } from 'react';

import { Flex } from '../Layout';
import { Heading, Paragraph } from '../Text';
import { Tooltip } from '../Tooltip';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';

interface CardHeaderProps<T extends keyof ReactHTML = 'header'>
    extends SlottedContainerProps<T> {
    /**
     * The heading of the card header.
     */
    heading?: string | undefined;
    /**
     * The sub heading of the card header.
     */
    subHeading?: ReactNode | undefined;
    /**
     * Where to render the sub heading.
     * @default "inside"
     */
    subHeadingPlacement?: 'info-tooltip' | undefined;
    /**
     * The secondary actions of the card header.
     */
    secondaryActions?: ReactNode | undefined;
    /**
     * The logo of the card header.
     */
    logo?: ReactNode | undefined;
}

const styles = stylex.create({
    headingContainer: {
        overflow: 'hidden',
    },
    heading: {
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        textWrap: 'nowrap',
    },
    info: {
        alignItems: 'center',
        backgroundColor: 'transparent',
        borderWidth: 0,
        display: 'flex',
        justifyContent: 'center',
    },
});

const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
    (props, forwardedRef) => {
        const {
            heading,
            subHeading,
            secondaryActions,
            logo,
            subHeadingPlacement,
            children,
            ...otherProps
        } = props;
        return (
            <Flex
                direction="row"
                gap="2x"
                align={subHeading ? undefined : 'center'}
                asChild
            >
                <SlottedContainer
                    {...otherProps}
                    tag="header"
                    stylexProps={stylex.props()}
                    ref={forwardedRef}
                >
                    {logo && logo}
                    <Flex
                        direction="column"
                        gap="0_5x"
                        grow={1}
                        {...stylex.props(styles.headingContainer)}
                    >
                        {heading && (
                            <Flex gap="1x" align="center">
                                <Heading
                                    size="subHeader"
                                    {...stylex.props(styles.heading)}
                                >
                                    {heading}
                                </Heading>
                                {subHeadingPlacement === 'info-tooltip' &&
                                    subHeading && (
                                        <Tooltip text={subHeading as string}>
                                            <button
                                                {...stylex.props(styles.info)}
                                                aria-label={
                                                    subHeading as string
                                                }
                                            >
                                                <InfoCircleIcon />
                                            </button>
                                        </Tooltip>
                                    )}
                            </Flex>
                        )}
                        {subHeading && !subHeadingPlacement && (
                            <Paragraph variant="secondary" size="small">
                                {subHeading}
                            </Paragraph>
                        )}
                        <Slottable>{children}</Slottable>
                    </Flex>
                    {secondaryActions && secondaryActions}
                </SlottedContainer>
            </Flex>
        );
    },
);
CardHeader.displayName = 'Card.Header';
export type { CardHeaderProps };
export { CardHeader };
