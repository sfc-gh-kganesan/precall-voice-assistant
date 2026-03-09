import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { IconContextProvider } from '@snowflake/stellar-icons';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';

import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import {
    SlottedContainer,
    type SlottedContainerProps,
} from '../util/SlottedContainer';

interface EditorialProps<T extends keyof ReactHTML = 'div'>
    extends SlottedContainerProps<T> {
    /**
     * The size of the editorial text.
     * @default "large"
     */
    size: 'large' | 'larger';
}

const styles = stylex.create({
    editorial: {
        color: baltoTheme.reusableTextHeader,
        margin: 0,
        padding: 0,
        textWrap: 'balance',
        wordBreak: 'break-word',
    },
});

const Editorial = forwardRef<HTMLDivElement, EditorialProps>(
    (props, forwardedRef) => {
        const { size, ...otherProps } = props;

        const textStyles = useTypeRamp(
            size === 'large'
                ? 'largeEditorialHeadline'
                : 'largerEditorialHeadline',
        );
        return (
            <IconContextProvider>
                <SlottedContainer
                    {...otherProps}
                    tag="div"
                    stylexProps={stylex.props(textStyles, styles.editorial)}
                    ref={forwardedRef}
                />
            </IconContextProvider>
        );
    },
);

Editorial.displayName = 'Editorial';
export type { EditorialProps };
export { Editorial };
