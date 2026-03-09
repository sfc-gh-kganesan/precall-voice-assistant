import type { ReactHTML } from 'react';
import { useContext } from 'react';

import type { HeadingLevel } from './HeadingContext';
import { HeadingContext } from './HeadingContext';

interface HeadingTagResult {
    tag: keyof ReactHTML;
}
const useHeadingTag = (): HeadingTagResult => {
    const headingCtx = useContext(HeadingContext);
    const headingLevel: HeadingLevel = headingCtx?.level ?? 1;
    const tag = `h${headingLevel}` as 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
    return { tag };
};

export { useHeadingTag };
export type { HeadingTagResult };
