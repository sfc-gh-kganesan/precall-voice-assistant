import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes } from 'react';
import { forwardRef, useContext } from 'react';

import type { ButtonSize, ButtonVariant } from '../Button';
import { useMergedStyles } from '../hooks';
import { SizeContext } from '../util/context';
import { SplitButtonAction } from './SplitButtonAction';
import { SplitButtonContext } from './SplitButtonContext';
import { SplitButtonTrigger } from './SplitButtonTrigger';

interface SplitButtonProps extends HTMLAttributes<HTMLDivElement> {
    /**
     * The variant of the split button.
     * @default "primary"
     */
    variant?: Extract<ButtonVariant, 'primary' | 'secondary'> | undefined;
    /**
     * The size of the split button.
     * @default "regular"
     */
    size?: ButtonSize | undefined;
    /**
     * Whether the split button is disabled.
     * @default false
     */
    disabled?: boolean | undefined;
}

const styles = stylex.create({
    container: {
        display: 'flex',
        flexDirection: 'row',
        gap: 0,
    },
});

const SplitButtonComponent = forwardRef<HTMLDivElement, SplitButtonProps>(
    (props, forwardedRef) => {
        const contextSize = useContext(SizeContext);
        const {
            className,
            style,
            variant = 'primary',
            size: sizeProp,
            disabled,
            ...otherProps
        } = props;
        const size = sizeProp || contextSize || 'regular';

        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(styles.container),
        );

        return (
            <SplitButtonContext.Provider value={{ variant, size, disabled }}>
                <div ref={forwardedRef} {...mergedStyles} {...otherProps} />
            </SplitButtonContext.Provider>
        );
    },
);
SplitButtonComponent.displayName = 'SplitButton.Root';

export type { SplitButtonProps };
export type { SplitButtonActionProps } from './SplitButtonAction';
export type { SplitButtonTriggerProps } from './SplitButtonTrigger';
export {
    SplitButtonComponent as Root,
    SplitButtonAction as Action,
    SplitButtonTrigger as Trigger,
};
