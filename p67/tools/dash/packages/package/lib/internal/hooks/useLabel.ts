import { useContext } from 'react';

import { FieldContext } from '../../Form/FormContext';
import { devError } from '../../util/dev-warning';

interface AriaLabelableProps {
    'aria-label'?: string;
    'aria-labelledby'?: string;
    id?: string;
}

declare global {
    interface Window {
        __REACT_DEVTOOLS_GLOBAL_HOOK__: unknown;
    }
}

export function useAriaLabel(props: AriaLabelableProps) {
    const fieldContext = useContext(FieldContext);

    if (fieldContext === null) {
        if (!props['aria-label'] && !props['aria-labelledby'] && !props.id) {
            devError(
                'aria-label or aria-labelledby is required when not used inside a Field.',
            );
        }
    }

    // If we aren't showing a visible label, use the aria-label
    if (fieldContext?.showLabel === false) {
        return {
            ariaLabelProps: {
                'aria-label': props['aria-label'] || fieldContext?.label,
                'aria-labelledby': undefined,
            },
        };
    }

    return {
        ariaLabelProps: {
            'aria-label': fieldContext?.labelId
                ? undefined
                : props['aria-label'] || fieldContext?.label,
            'aria-labelledby':
                props['aria-labelledby'] || fieldContext?.labelId,
        },
    };
}
