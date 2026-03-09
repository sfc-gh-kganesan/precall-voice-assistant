import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';

import { Flex } from '../Layout';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';

type CardFooterProps<T extends keyof ReactHTML = 'footer'> =
    SlottedContainerProps<T>;

const CardFooter = forwardRef<HTMLDivElement, CardFooterProps>(
    (props, forwardedRef) => {
        return (
            <Flex direction="row" gap="1x" asChild>
                <SlottedContainer
                    {...props}
                    tag="footer"
                    stylexProps={stylex.props()}
                    ref={forwardedRef}
                />
            </Flex>
        );
    },
);
CardFooter.displayName = 'Card.Footer';
export type { CardFooterProps };
export { CardFooter };
