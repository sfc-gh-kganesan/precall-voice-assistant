import { ChevronDownBoldIcon, ChevronDownIcon } from '@snowflake/stellar-icons';
import * as stylex from '@stylexjs/stylex';
import { forwardRef, useContext } from 'react';
import type { IconButtonProps } from '../Button';
import { IconButton } from '../Button';
import { useMergedStyles } from '../hooks';
import { SplitButtonContext } from './SplitButtonContext';

type SplitButtonTriggerProps = Omit<
    IconButtonProps,
    'variant' | 'size' | 'icon'
>;

const styles = stylex.create({
    trigger: {
        borderBottomLeftRadius: 0,
        borderTopLeftRadius: 0,
    },
});

const SplitButtonTrigger = forwardRef<
    HTMLButtonElement,
    SplitButtonTriggerProps
>((props, forwardedRef) => {
    const splitButtonContext = useContext(SplitButtonContext);
    const { className, style, ...otherProps } = props;

    const mergedStyles = useMergedStyles(
        className,
        style,
        stylex.props(styles.trigger),
    );

    return (
        <IconButton
            {...(otherProps as IconButtonProps)}
            {...mergedStyles}
            variant={splitButtonContext.variant}
            size={splitButtonContext.size}
            icon={
                splitButtonContext.variant === 'primary'
                    ? ChevronDownBoldIcon
                    : ChevronDownIcon
            }
            disabled={splitButtonContext.disabled ?? otherProps.disabled}
            ref={forwardedRef}
        />
    );
});

SplitButtonTrigger.displayName = 'SplitButton.Trigger';
export type { SplitButtonTriggerProps };
export { SplitButtonTrigger };
