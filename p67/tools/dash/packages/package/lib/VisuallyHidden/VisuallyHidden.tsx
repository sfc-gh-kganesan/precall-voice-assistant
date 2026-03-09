import { VisuallyHidden as ReactAriaVisuallyHidden } from 'react-aria';

interface VisuallyHiddenProps {
    /**
     * The children to be hidden visually.
     */
    children: React.ReactNode;
}

/**
 * VisuallyHidden hides its children visually, while keeping content visible
 * to screen readers.
 */
export function VisuallyHidden(props: VisuallyHiddenProps) {
    return <ReactAriaVisuallyHidden {...props} />;
}
