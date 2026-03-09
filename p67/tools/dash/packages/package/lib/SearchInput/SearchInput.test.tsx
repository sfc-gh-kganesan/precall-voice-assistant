/* eslint-disable @typescript-eslint/no-non-null-assertion */

import '@testing-library/jest-dom/vitest';

import { fireEvent, render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { SearchInput } from './SearchInput';

describe('SearchInput', () => {
    it('should be clearable', async () => {
        const result = render(<SearchInput aria-label="Search" />);

        const input = result.container.querySelector('input')!;
        expect(input).toBeInTheDocument();

        let clearButton = result.container.querySelector('button');
        expect(clearButton).not.toBeInTheDocument();

        // type into input
        fireEvent.change(input, { target: { value: 'test' } });
        expect(input).toHaveValue('test');

        // click clear button
        clearButton = result.container.querySelector('button')!;
        expect(clearButton).toBeInTheDocument();
        fireEvent.click(clearButton);
        expect(input).toHaveValue('');
    });
});
