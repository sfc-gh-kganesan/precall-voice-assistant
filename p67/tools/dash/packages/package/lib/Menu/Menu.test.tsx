import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';
import { BaltoProvider } from '../BaltoProvider';
import { Button } from '../Button';
import * as Menu from './Menu';

describe('Menu', () => {
    afterEach(cleanup);

    it('renders with default props', async () => {
        const user = userEvent.setup();

        render(
            <BaltoProvider colorScheme="light">
                <Menu.Root trigger={<Button>Open</Button>}>
                    <Menu.Item label="Item 1" />
                    <Menu.Item label="Item 2" shouldAutoFocusOnSelect={false} />
                </Menu.Root>
            </BaltoProvider>,
        );

        const button = screen.getByText('Open').closest('button');

        if (!button) {
            // eslint-disable-next-line no-restricted-syntax
            throw new Error('Button not found');
        }

        expect(button).toBeInTheDocument();

        await user.click(button);

        const item1 = screen.getByRole('menuitem', { name: 'Item 1' });
        expect(item1).toBeInTheDocument();

        await user.click(item1);
        expect(button).toHaveFocus();

        await user.click(button);

        const item2 = screen.getByRole('menuitem', { name: 'Item 2' });
        expect(item2).toBeInTheDocument();

        await user.click(item2);
        expect(button).not.toHaveFocus();
    });
});
