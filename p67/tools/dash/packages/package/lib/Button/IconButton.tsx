import type { IconType } from '@snowflake/stellar-icons';
import { forwardRef } from 'react';
import { useAriaLabel } from '../internal/hooks/useLabel';
import type { SlottedButtonContainerProps } from '../util/SlottedContainer';
import { Button } from './Button';
import type { ButtonSize, ButtonVariant } from './types';
import { IsIconOnlyContext } from './useButtonStyles';

interface IconButtonBaseProps
    extends Omit<SlottedButtonContainerProps, 'asChild' | 'children'> {
    /**
     * The variant of the button.
     */
    variant?: ButtonVariant | undefined;
    /**
     * The size of the button.
     * @default "regular"
     */
    size?: ButtonSize | undefined;
    /**
     * Whether the button is disabled.
     * @default false
     */
    disabled?: boolean | undefined;
    /**
     * Whether the button is selected.
     * @default false
     */
    selected?: boolean | undefined;
    /**
     * The icon of the button.
     */
    icon: IconType;
    /**
     * Whether the button is loading.
     * @default false
     */
    isLoading?: boolean | undefined;
}

interface IconButtonNoChildrenProps {
    /**
     * The default button should not have children.
     */
    children?: never | undefined;
    /**
     * The default button should not be rendered as a child.
     */
    asChild?: never | undefined;
}

interface IconButtonAsChildProps {
    /**
     * The element the button will render as.
     */
    children: React.ReactNode;
    /**
     * When this property is set to true, Balto will not render a default DOM element,
     * instead cloning the part's child and passing it the props and behavior required to make it functional.
     *
     * This will break props that only work on specific HTML tags since Balto delegates to the browser for all
     * default behaviors of html tags.
     */
    asChild: true;
}

interface IconButtonAriaLabelProps extends IconButtonBaseProps {
    /**
     * The aria label of the button.
     */
    'aria-label': string;
}

interface IconButtonAriaLabelledbyProps extends IconButtonBaseProps {
    /**
     * The aria labelled by of the button.
     */
    'aria-labelledby': string;
}

type IconButtonProps = (
    | IconButtonAriaLabelProps
    | IconButtonAriaLabelledbyProps
) &
    (IconButtonNoChildrenProps | IconButtonAsChildProps);

const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
    (
        {
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledby,
            ...props
        },
        forwardedRef,
    ) => {
        const { icon, ...otherProps } = props;
        const { ariaLabelProps } = useAriaLabel({
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledby,
        });

        return (
            <IsIconOnlyContext.Provider value={true}>
                <Button
                    {...ariaLabelProps}
                    {...otherProps}
                    prefixIcon={icon}
                    ref={forwardedRef}
                />
            </IsIconOnlyContext.Provider>
        );
    },
);

IconButton.displayName = 'IconButton';
export type { IconButtonProps };
export { IconButton };
