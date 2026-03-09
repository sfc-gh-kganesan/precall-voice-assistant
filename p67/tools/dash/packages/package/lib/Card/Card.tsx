import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';
import { Flex } from '../Layout';
import {
    HeadingContext,
    useCreateHeadingContext,
} from '../Text/internal/HeadingContext';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';
import type { CardBodyProps } from './CardBody';
import { CardBody } from './CardBody';
import type { CardFooterProps } from './CardFooter';
import { CardFooter } from './CardFooter';
import type { CardHeaderProps } from './CardHeader';
import { CardHeader } from './CardHeader';
import { cardStyles } from './cardStyles';

type CardProps<T extends keyof ReactHTML = 'section'> =
    SlottedContainerProps<T>;

const Root = forwardRef<HTMLDivElement, CardProps>((props, forwardedRef) => {
    const headingContext = useCreateHeadingContext();
    return (
        <HeadingContext.Provider value={headingContext}>
            <Flex direction="column" gap="2x" grow={1} shrink={1} asChild>
                <SlottedContainer
                    {...props}
                    tag="section"
                    stylexProps={stylex.props(cardStyles.default)}
                    ref={forwardedRef}
                />
            </Flex>
        </HeadingContext.Provider>
    );
});
Root.displayName = 'Card.Root';

export type { CardProps, CardBodyProps, CardHeaderProps, CardFooterProps };
export { Root, CardBody as Body, CardHeader as Header, CardFooter as Footer };
