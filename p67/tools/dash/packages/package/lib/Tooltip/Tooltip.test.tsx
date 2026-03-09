import { render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { BaltoProvider } from '../BaltoProvider';
import { Tooltip } from './Tooltip';

describe('Tooltip', () => {
    it('logs a warning when nesting Tooltip', () => {
        const consoleSpy = vi
            .spyOn(console, 'warn')
            .mockImplementation(() => {});

        render(
            <BaltoProvider colorScheme="light">
                <Tooltip text="tooltip text">
                    <div>
                        Hover me
                        <Tooltip text="nested tooltip">
                            <div>nested</div>
                        </Tooltip>
                    </div>
                </Tooltip>
            </BaltoProvider>,
        );

        expect(consoleSpy).toHaveBeenCalledWith(
            'Tooltip should not be nested.',
        );
    });
});
