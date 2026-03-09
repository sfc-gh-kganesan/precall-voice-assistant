import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRef, useState } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { BaltoProvider } from '../BaltoProvider';
import { Button } from '../Button';
import * as Dialog from './Dialog';

const DialogFocusElsewhere = () => {
    const [open, setOpen] = useState(false);
    const buttonRef = useRef<HTMLButtonElement>(null);
    const onCloseAutoFocus = () => {
        buttonRef.current?.focus();
    };

    return (
        <BaltoProvider colorScheme="light">
            <Dialog.Root
                trigger={<Button>Open</Button>}
                onCloseAutoFocus={onCloseAutoFocus}
                open={open}
                onOpenChange={setOpen}
            >
                <Dialog.Header
                    heading="Interaction"
                    subHeading="This dialog only closes when the user clicks the close button"
                />
                <Dialog.Footer
                    primaryCtaArea={
                        <Button onClick={() => setOpen(false)}>Close</Button>
                    }
                />
            </Dialog.Root>
            <Button ref={buttonRef} id="other-button">
                Other button
            </Button>
        </BaltoProvider>
    );
};

describe('Dialog', () => {
    afterEach(cleanup);

    it('can control focus when closing', async () => {
        const user = userEvent.setup();

        render(<DialogFocusElsewhere />);

        const button = screen.getByText('Open');
        expect(button).toBeInTheDocument();

        await user.click(button);

        const dialog = screen.getByRole('dialog', { name: 'Interaction' });
        expect(dialog).toBeInTheDocument();

        const closeButton = screen.getByText('Close');
        await user.click(closeButton);

        expect(dialog).not.toBeInTheDocument();

        const otherButton = screen.getByText('Other button');
        expect(otherButton.closest('button')).toHaveFocus();
    });
});
