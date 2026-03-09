import { useCallback, useEffect } from 'react';

interface UseAutoresizeTextareaProps {
    /**
     * The ref to the textarea element
     */
    textareaRef:
        | React.RefObject<HTMLTextAreaElement | null>
        | React.MutableRefObject<HTMLTextAreaElement | undefined>;
    /**
     * The value of the textarea
     */
    value?: string | number | readonly string[];
    /**
     * Whether auto-resize is enabled
     */
    enabled?: boolean;
    /**
     * Minimum height for the textarea in pixels
     * @default undefined (uses natural height)
     */
    minHeight?: number;
    /**
     * Maximum height for the textarea in pixels
     * @default undefined (no limit)
     */
    maxHeight?: number;
}

/**
 * Hook that automatically resizes a textarea based on its content
 */
export function useAutoresizeTextarea({
    textareaRef,
    value,
    enabled = false,
    minHeight,
    maxHeight,
}: UseAutoresizeTextareaProps) {
    const resizeTextarea = useCallback(() => {
        if (!enabled || !textareaRef.current) {
            return;
        }

        const textarea = textareaRef.current;

        // Reset height to auto to get the actual scrollHeight
        textarea.style.height = 'auto';

        // Calculate the new height
        let newHeight = textarea.scrollHeight;

        // Apply min/max height constraints
        if (minHeight !== undefined) {
            newHeight = Math.max(newHeight, minHeight);
        }
        if (maxHeight !== undefined) {
            newHeight = Math.min(newHeight, maxHeight);
        }

        // Set the new height
        textarea.style.height = `${newHeight}px`;

        // Handle overflow when content exceeds maxHeight
        if (maxHeight !== undefined && textarea.scrollHeight > maxHeight) {
            textarea.style.overflowY = 'auto';
        } else {
            textarea.style.overflowY = 'hidden';
        }
    }, [enabled, textareaRef, minHeight, maxHeight]);

    // Resize when value changes
    useEffect(() => {
        resizeTextarea();
    }, [value, resizeTextarea]);

    // Set up initial state and resize on mount
    useEffect(() => {
        if (!enabled || !textareaRef.current) {
            return;
        }

        const textarea = textareaRef.current;

        // Store original styles so we can restore them if needed
        const originalResize = textarea.style.resize;
        const originalOverflow = textarea.style.overflowY;

        // Set initial styles for auto-resize
        textarea.style.resize = 'none';
        textarea.style.overflowY = 'hidden';

        // Initial resize
        resizeTextarea();

        // Add input event listener for real-time resizing
        const handleInput = () => {
            resizeTextarea();
        };

        textarea.addEventListener('input', handleInput);

        // Cleanup function
        return () => {
            textarea.removeEventListener('input', handleInput);
            // Restore original styles if component unmounts
            textarea.style.resize = originalResize;
            textarea.style.overflowY = originalOverflow;
        };
    }, [enabled, textareaRef, resizeTextarea]);

    return {
        /**
         * Function to manually trigger a resize
         */
        resize: resizeTextarea,
    };
}
