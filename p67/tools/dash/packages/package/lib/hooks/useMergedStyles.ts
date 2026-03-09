import { clsx } from 'clsx';
import type { CSSProperties } from 'react';
import { useMemo } from 'react';

interface StyleProps {
    className?: string;
    style?: CSSProperties;
}
const useMergedStyles = (
    className: string | undefined,
    style: CSSProperties | undefined,
    fromStylex: Readonly<StyleProps>,
): Readonly<StyleProps> =>
    useMemo(
        () => ({
            className: clsx(className, fromStylex.className),
            style: { ...style, ...fromStylex.style },
        }),
        [className, style, fromStylex.className, fromStylex.style],
    );
export { useMergedStyles };
export type { StyleProps };
