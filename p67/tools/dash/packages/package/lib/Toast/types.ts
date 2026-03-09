import type { StatusVariant } from '../Status';

export type ToastVariant = Extract<
    StatusVariant,
    'neutral' | 'success' | 'critical'
>;
