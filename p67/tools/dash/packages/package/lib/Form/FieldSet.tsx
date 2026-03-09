import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';
import { Flex } from '../Layout/Flex';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';
import type { FormFlexDirection } from './FormContext';
import { FormContext } from './FormContext';

interface FieldSetProps<T extends keyof ReactHTML = 'fieldset'>
    extends SlottedContainerProps<T> {
    /**
     * The direction of labels and controls in the fieldset.
     * If not provided, the fieldset will be responsive.
     */
    direction?: FormFlexDirection | undefined;
}

const styles = stylex.create({
    fieldSet: {
        borderWidth: 0,
        containerType: 'inline-size', // Required to use @container query CSS styles on its children.
        flexGrow: 1,
        margin: 0,
        padding: 0,
    },
});

const FieldSet = forwardRef<HTMLFieldSetElement, FieldSetProps>(
    (props, forwardedRef) => {
        const { direction, ...otherProps } = props;

        return (
            <FormContext.Provider
                value={{ variant: 'regular', fieldFlexDirection: direction }}
            >
                <Flex direction="column" gap="3x" asChild>
                    <SlottedContainer
                        {...otherProps}
                        tag="fieldset"
                        ref={forwardedRef}
                        stylexProps={stylex.props(styles.fieldSet)}
                    />
                </Flex>
            </FormContext.Provider>
        );
    },
);

FieldSet.displayName = 'FieldSet';
export type { FieldSetProps };
export { FieldSet };
