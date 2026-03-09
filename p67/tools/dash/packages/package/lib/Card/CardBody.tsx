import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';

import { Flex } from '../Layout';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';

type CardBodyProps<T extends keyof ReactHTML = 'div'> =
    SlottedContainerProps<T>;

const CardBody = forwardRef<HTMLDivElement, CardBodyProps>(
    (props, forwardedRef) => {
        return (
            <Flex direction="column" grow={1} shrink={1} asChild>
                <SlottedContainer
                    {...props}
                    tag="div"
                    stylexProps={stylex.props()}
                    ref={forwardedRef}
                />
            </Flex>
        );
    },
);
CardBody.displayName = 'Card.Body';
export type { CardBodyProps };
export { CardBody };
