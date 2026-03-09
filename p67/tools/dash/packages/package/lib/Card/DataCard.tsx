import { Slottable } from '@radix-ui/react-slot';
import * as stylex from '@stylexjs/stylex';
import { forwardRef, useContext } from 'react';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { Flex } from '../Layout';
import { SizeContext } from '../main';
import { OverflowTooltip } from '../OverflowTooltip';
import { Paragraph } from '../Text';
import {
    type SlottedButtonContainerProps,
    SlottedContainer,
} from '../util/SlottedContainer';
import { cardStyles, dataCardStyles } from './cardStyles';
import type { DataCardSize } from './types';

interface BaseDataCardProps {
    /**
     * The heading of the data card.
     */
    heading?: string | undefined;
    /**
     * The sub heading of the data card.
     */
    subHeading?: string | undefined;
    /**
     * The size of the data card.
     * @default "regular"
     */
    size?: DataCardSize | undefined;
}
interface DataCardProps
    extends BaseDataCardProps,
        SlottedButtonContainerProps {}

interface SelectableDataCardProps
    extends BaseDataCardProps,
        SlottedButtonContainerProps {
    /**
     * Whether the data card is selected.
     * @default false
     */
    selected?: boolean | undefined;
}

const DataCard = forwardRef<HTMLDivElement, DataCardProps>((props, ref) => {
    const contextSize = useContext(SizeContext);
    const {
        heading,
        subHeading,
        size = contextSize ?? 'regular',
        children,
        ...otherProps
    } = props;

    const headingTextStyles = useTypeRamp(
        size === 'small' ? 'pageHeader' : 'largeEditorialHeadline',
    );

    return (
        <Flex direction="column" gap="2x" grow={1} shrink={1} asChild>
            <SlottedContainer
                tag="div"
                ref={ref}
                {...otherProps}
                stylexProps={stylex.props(
                    cardStyles.default,
                    dataCardStyles.default,
                    size === 'small' && dataCardStyles.small,
                )}
            >
                {heading && (
                    <OverflowTooltip.Root asChild>
                        <SlottedContainer
                            tag="div"
                            stylexProps={stylex.props(headingTextStyles)}
                        >
                            {heading}
                        </SlottedContainer>
                    </OverflowTooltip.Root>
                )}
                {subHeading && (
                    <Paragraph size={size} variant="secondary">
                        {subHeading}
                    </Paragraph>
                )}
                <Slottable>{children}</Slottable>
            </SlottedContainer>
        </Flex>
    );
});

DataCard.displayName = 'DataCard';

const DataCardSelectable = forwardRef<
    HTMLButtonElement,
    SelectableDataCardProps
>((props, ref) => {
    const contextSize = useContext(SizeContext);
    const {
        heading,
        subHeading,
        size = contextSize ?? 'regular',
        selected,
        children,
        ...otherProps
    } = props;

    const headingTextStyles = useTypeRamp(
        size === 'small' ? 'pageHeader' : 'largeEditorialHeadline',
    );

    return (
        <Flex direction="column" gap="2x" grow={1} shrink={1} asChild>
            <SlottedContainer
                tag="button"
                ref={ref}
                {...otherProps}
                stylexProps={stylex.props(
                    cardStyles.default,
                    cardStyles.selectable,
                    selected && cardStyles.selected,
                    dataCardStyles.default,
                    size === 'small' && dataCardStyles.small,
                )}
            >
                {heading && (
                    <OverflowTooltip.Root asChild>
                        <SlottedContainer
                            tag="div"
                            stylexProps={stylex.props(headingTextStyles)}
                        >
                            {heading}
                        </SlottedContainer>
                    </OverflowTooltip.Root>
                )}
                {subHeading && (
                    <Paragraph size={size} variant="secondary">
                        {subHeading}
                    </Paragraph>
                )}
                <Slottable>{children}</Slottable>
            </SlottedContainer>
        </Flex>
    );
});

DataCardSelectable.displayName = 'DataCardSelectable';

export { DataCard, DataCardSelectable };
export type { DataCardProps, SelectableDataCardProps };
