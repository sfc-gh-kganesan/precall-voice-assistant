import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import * as stylex from '@stylexjs/stylex';
import { forwardRef, useContext } from 'react';
import type { ButtonProps } from '../Button';
import { Button } from '../Button';
import { useMergedStyles } from '../hooks';
import { SplitButtonContext } from './SplitButtonContext';

type SplitButtonActionProps = Omit<ButtonProps, 'variant' | 'size'>;

const styles = stylex.create({
    action: {
        borderBottomRightRadius: 0,
        borderRightWidth: 0,
        borderTopRightRadius: 0,
    },
    actionWithDivider: {
        borderRightColor: baltoTheme.reusableBorderDefault,
        borderRightStyle: 'solid',
        borderRightWidth: 1,
    },
});

const SplitButtonAction = forwardRef<HTMLButtonElement, SplitButtonActionProps>(
    (props, forwardedRef) => {
        const splitButtonContext = useContext(SplitButtonContext);
        const { className, style, ...otherProps } = props;

        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(
                styles.action,
                splitButtonContext.variant === 'primary' &&
                    styles.actionWithDivider,
            ),
        );

        return (
            <Button
                {...otherProps}
                {...mergedStyles}
                disabled={splitButtonContext.disabled ?? otherProps.disabled}
                variant={splitButtonContext.variant}
                size={splitButtonContext.size}
                ref={forwardedRef}
            />
        );
    },
);

SplitButtonAction.displayName = 'SplitButton.Action';
export type { SplitButtonActionProps };
export { SplitButtonAction };
