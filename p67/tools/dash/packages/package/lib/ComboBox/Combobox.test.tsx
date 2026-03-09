import { cleanup, render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';
import { BaltoProvider } from '../BaltoProvider';
import * as ComboBox from './ComboBox';

afterEach(cleanup);

describe('ComboBox', () => {
    it('opens when you type', async () => {
        const { findByRole, getByText } = render(
            <BaltoProvider colorScheme="light">
                <ComboBox.Root aria-label="Test">
                    <ComboBox.Option label="Item 1" />
                    <ComboBox.Option label="Item 2" />
                    <ComboBox.Option label="Item 3" />
                </ComboBox.Root>
            </BaltoProvider>,
        );

        const inputControl = await findByRole('combobox');
        expect(inputControl).toBeInTheDocument();

        await userEvent.click(inputControl);
        await userEvent.type(inputControl, 'Item 1');

        const listbox = await findByRole('listbox');
        expect(listbox).toBeInTheDocument();

        await userEvent.keyboard('[Enter]');
        expect(listbox).not.toBeInTheDocument();

        expect(getByText('Item 1')).toBeInTheDocument();
    });

    it('opens when you click the chevron', async () => {
        const { findByRole } = render(
            <BaltoProvider colorScheme="light">
                <ComboBox.Root aria-label="Test" hasChevron>
                    <ComboBox.Option label="Item 1" />
                    <ComboBox.Option label="Item 2" />
                    <ComboBox.Option label="Item 3" />
                </ComboBox.Root>
            </BaltoProvider>,
        );

        const chevron = await findByRole('button');
        expect(chevron).toBeInTheDocument();

        await userEvent.click(chevron);

        const listbox = await findByRole('listbox');
        expect(listbox).toBeInTheDocument();
    });

    it('can open the combobox with the keyboard', async () => {
        const { findByRole, getByText } = render(
            <BaltoProvider colorScheme="light">
                <ComboBox.Root aria-label="Test">
                    <ComboBox.Option label="Item 1" />
                    <ComboBox.Option label="Item 2" />
                    <ComboBox.Option label="Item 3" />
                </ComboBox.Root>
            </BaltoProvider>,
        );

        const inputControl = await findByRole('combobox');
        expect(inputControl).toBeInTheDocument();

        await userEvent.click(inputControl);
        await userEvent.keyboard('[ArrowDown]');

        const listbox = await findByRole('listbox');
        expect(listbox).toBeInTheDocument();

        const item1 = await findByRole('option', { name: 'Item 1' });
        expect(item1).toBeInTheDocument();

        await userEvent.click(item1);
        expect(listbox).not.toBeInTheDocument();

        expect(getByText('Item 1')).toBeInTheDocument();
    });

    it('opens when openOnFocus is true', async () => {
        const { findByRole } = render(
            <BaltoProvider colorScheme="light">
                <ComboBox.Root aria-label="Test" openOnFocus>
                    <ComboBox.Option label="Item 1" />
                    <ComboBox.Option label="Item 2" />
                    <ComboBox.Option label="Item 3" />
                </ComboBox.Root>
            </BaltoProvider>,
        );

        const inputControl = await findByRole('combobox');
        expect(inputControl).toBeInTheDocument();

        await userEvent.click(inputControl);

        const listbox = await findByRole('listbox');
        expect(listbox).toBeInTheDocument();
    });
});
