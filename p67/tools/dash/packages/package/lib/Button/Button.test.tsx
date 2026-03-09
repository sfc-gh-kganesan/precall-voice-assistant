import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Button } from './Button';

describe('Button', () => {
    afterEach(cleanup);

    it('renders with default props', () => {
        render(<Button>Click me</Button>);

        const button = screen.getByText('Click me');
        expect(button).toBeInTheDocument();
    });

    it('handles click events', () => {
        const handleClick = vi.fn();

        render(<Button onClick={handleClick}>Clickable Button</Button>);

        const button = screen.getByText('Clickable Button');
        fireEvent.click(button);
        expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('ignores click events when disabled', () => {
        const handleClick = vi.fn();

        render(
            <Button disabled onClick={handleClick}>
                Clickable Button
            </Button>,
        );

        const button = screen.getByText('Clickable Button');
        fireEvent.click(button);
        expect(handleClick).toHaveBeenCalledTimes(0);
    });

    it('handles form submission', async () => {
        const handleSubmit = vi.fn();

        render(
            <form onSubmit={handleSubmit}>
                <Button type="submit">Clickable Button</Button>
            </form>,
        );

        // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
        const button = screen.getByText('Clickable Button').closest('button')!;
        await userEvent.click(button);
        expect(handleSubmit).toHaveBeenCalledTimes(1);
    });

    it('ignores click events and does not submit form when disabled', () => {
        const handleSubmit = vi.fn();

        render(
            <form onSubmit={handleSubmit}>
                <Button disabled>Clickable Button</Button>
            </form>,
        );

        const button = screen.getByText('Clickable Button');
        fireEvent.click(button);
        expect(handleSubmit).toHaveBeenCalledTimes(0);
    });
});
