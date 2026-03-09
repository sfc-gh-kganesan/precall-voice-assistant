const textVariants = ['primary', 'secondary', 'critical', 'caution'] as const;
type TextVariant = (typeof textVariants)[number];

export { textVariants };
export type { TextVariant };
