import type { Size } from '../types';

type DialogSize =
    | Extract<Size, 'small' | 'medium' | 'large' | 'xlarge'>
    | 'fullscreen';

export type { DialogSize };
