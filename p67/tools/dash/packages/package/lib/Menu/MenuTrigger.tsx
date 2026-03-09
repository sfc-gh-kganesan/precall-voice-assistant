import type { DOMAttributes, ReactElement } from 'react';
import { forwardRef, useEffect, useMemo, useRef } from 'react';
import type { ButtonProps } from 'react-aria-components';
import { Pressable } from 'react-aria-components';
import { useMergedRef } from '../internal/hooks/useMergedRef';
import type { FocusableElement } from '../types';
import { useAutoFocusContext } from './AutoFocusContext';

type MenuTriggerProps = Omit<ButtonProps, 'children'> & {
    /**
     * The children of the menu trigger.
     */
    children: ReactElement<
        DOMAttributes<FocusableElement> & {
            /**
             * Whether the menu trigger is disabled.
             */
            disabled?: boolean | undefined;
        },
        string
    >;
};

export const MenuTrigger = forwardRef(function MenuTrigger(
    props: MenuTriggerProps,
    ref: React.ForwardedRef<HTMLButtonElement>,
) {
    const innerRef = useRef<HTMLButtonElement>(null);
    const mergedRef = useMergedRef(ref, innerRef);
    const { shouldAutoFocusOnClose } = useAutoFocusContext('MenuTrigger');

    useEffect(() => {
        const el = innerRef.current;

        if (!el) return;

        const RESTORE_FOCUS_EVENT = 'react-aria-focus-scope-restore';

        const handleRestoreFocus = (e: Event) => {
            if (shouldAutoFocusOnClose) return;
            e.preventDefault();
        };

        el.addEventListener(RESTORE_FOCUS_EVENT, handleRestoreFocus);

        return () => {
            el.removeEventListener(RESTORE_FOCUS_EVENT, handleRestoreFocus);
        };
    }, [shouldAutoFocusOnClose]);

    const isChildDisabled = useMemo(
        () => Boolean(props.children.props.disabled),
        [props.children],
    );

    return (
        <Pressable
            ref={mergedRef}
            {...props}
            isDisabled={isChildDisabled}
            data-menu-trigger
        >
            {props.children}
        </Pressable>
    );
});
