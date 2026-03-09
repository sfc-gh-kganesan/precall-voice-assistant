import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Card } from '../Card';
import { StatusBanner } from '../Status';
import { Heading } from './Heading';

describe('Heading can', () => {
    it('render subHeading as H1 when standalone', async () => {
        const result = render(<Heading size="subHeader">test</Heading>);
        const h1 = result.container.querySelector('h1');
        expect(h1?.textContent).toBe('test');
    });
    it('render card header as H1 when standalone', async () => {
        const result = render(
            <Card.Root>
                <Card.Header heading="card title" />
            </Card.Root>,
        );
        const h1 = result.container.querySelector('h1');
        expect(h1?.textContent).toBe('card title');
    });

    it('render nested H1 and H2 when using surfaces', async () => {
        const result = render(
            <Card.Root>
                <Card.Header heading="card title" />
                <Card.Body>
                    <StatusBanner heading="status banner title" />
                </Card.Body>
            </Card.Root>,
        );
        const h1 = result.container.querySelector('h1');
        expect(h1?.textContent).toBe('card title');
        const h2 = result.container.querySelector('h2');
        expect(h2?.textContent).toBe('status banner title');
    });
});
