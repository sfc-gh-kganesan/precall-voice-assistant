import { useLayoutEffect } from '@react-aria/utils';
import { useRef } from 'react';

/**
 * A React hook that returns a ref that always points to the latest value of a variable
 *
 * @param current The value to always point to
 * @returns A ref that always points to the latest value of a variable
 */
const useLatest = <T>(current: T) => {
    const storedValue = useRef(current);
    useLayoutEffect(() => {
        storedValue.current = current;
    });
    return storedValue;
};

export { useLatest };
