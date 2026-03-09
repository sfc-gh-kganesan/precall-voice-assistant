import type { Breakpoint } from '../types';

const largeBreakpoint = 1360;
const xLargeBreakpoint = 1680;
const breakPointToMaxWidth: Record<Breakpoint, number> = {
    initial: 0,
    xs: 479,
    sm: 719,
    md: 1023,
    lg: 1359,
    xl: 1679,
} as const;

export { breakPointToMaxWidth, largeBreakpoint, xLargeBreakpoint };
