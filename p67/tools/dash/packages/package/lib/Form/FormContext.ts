import { createContext } from 'react';

import type { FlexDirection } from '../Layout/Flex';

type FormFlexDirection = Extract<FlexDirection, 'row' | 'column'>;
interface FormContextType {
    variant: 'regular' | 'wide';
    fieldFlexDirection?: FormFlexDirection;
}
const FormContext = createContext<FormContextType | null>(null);

interface FieldContextType {
    label: string;
    showLabel: boolean | undefined;
    inputId?: string;
    labelId?: string;
    descriptionId?: string;
    success?: boolean;
    warning?: boolean;
    error?: boolean;
}
const FieldContext = createContext<FieldContextType | null>(null);

const generateFieldId = () => {
    return `field-${Math.random().toString(36).substring(2, 9)}`;
};

export { FormContext, FieldContext, generateFieldId };
export type { FormContextType, FieldContextType, FormFlexDirection };
