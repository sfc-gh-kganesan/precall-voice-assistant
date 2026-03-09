import { createContext } from '@radix-ui/react-context';

import type { Key } from '../types';

export const [MenuCheckboxSelectionContext, useMenuCheckboxSelectionContext] =
    createContext<{
        checked: Set<Key> | undefined;
        setChecked?: React.Dispatch<React.SetStateAction<Set<Key>>>;
    }>('MenuCheckboxSelectionContext', {
        checked: undefined,
        setChecked: undefined,
    });

export const [MenuSectionTypeContext, useMenuSectionTypeContext] =
    createContext<{
        type: 'radio' | 'checkbox' | undefined;
    }>('MenuSectionTypeContext', {
        type: undefined,
    });
