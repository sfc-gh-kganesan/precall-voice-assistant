import { isProd } from './isProd';

export const devWarning = (message: unknown) => {
    if (!isProd) {
        // eslint-disable-next-line no-restricted-syntax
        console.warn(message);
    }
};

export const devError = (message: string) => {
    if (!isProd) {
        // eslint-disable-next-line no-restricted-syntax
        throw new Error(message);
    }
};
