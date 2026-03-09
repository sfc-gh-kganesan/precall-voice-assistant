import { IconContextProvider } from '@snowflake/stellar-icons';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';
import type { SlottedContainerProps } from '../../util/SlottedContainer';
import { SlottedContainer } from '../../util/SlottedContainer';
import type { StatusVariant } from '../types';
import { StatusContext, useCreateStatusContext } from './StatusContext';
import { useStatusTextColors } from './useStatusColors';

interface StatusContainerProps<T extends keyof ReactHTML>
    extends SlottedContainerProps<T> {
    /**
     * The variant of the status container.
     */
    variant: StatusVariant;
    /**
     * The tag of the status container.
     */
    tag: T;
}

const StatusContainer = forwardRef<
    HTMLElement,
    StatusContainerProps<keyof ReactHTML>
>((props, forwardedRef) => {
    const { variant, tag, ...otherProps } = props;
    const contextValue = useCreateStatusContext(variant);
    const statusStyles = useStatusTextColors(variant, true);

    return (
        <StatusContext.Provider value={contextValue}>
            <IconContextProvider>
                <SlottedContainer
                    {...otherProps}
                    tag={tag}
                    ref={forwardedRef}
                    stylexProps={stylex.props(statusStyles)}
                />
            </IconContextProvider>
        </StatusContext.Provider>
    );
});

StatusContainer.displayName = 'StatusContainer';
export type { StatusContainerProps };
export { StatusContainer };
