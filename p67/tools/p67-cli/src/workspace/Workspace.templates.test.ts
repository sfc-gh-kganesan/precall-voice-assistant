import { describe, expect, test } from 'bun:test';
import { listTemplates } from '@p67-cli/workspace/Workspace';

describe('Workspace templates', () => {
    describe('listTemplates()', () => {
        test('should return expected template names', () => {
            const templates = listTemplates();
            expect(templates).toContain('hello-world');
            expect(templates).toContain('hitl');
        });

        test('should return an array with at least 2 templates', () => {
            const templates = listTemplates();
            expect(templates.length).toBeGreaterThanOrEqual(2);
        });
    });

    describe('template file imports', () => {
        test('hello-world index.ts.src should be resolvable', async () => {
            const ref = (
                await import(
                    '@p67-cli/workspace/templates/hello-world/src/index.ts.src',
                    { with: { type: 'file' } }
                )
            ).default;
            expect(typeof ref).toBe('string');
            expect(ref.length).toBeGreaterThan(0);
        });

        test('hello-world manifest.yaml.src should be resolvable', async () => {
            const ref = (
                await import(
                    '@p67-cli/workspace/templates/hello-world/manifest.yaml.src',
                    { with: { type: 'file' } }
                )
            ).default;
            expect(typeof ref).toBe('string');
            expect(ref.length).toBeGreaterThan(0);
        });

        test('hitl index.ts.src should be resolvable', async () => {
            const ref = (
                await import(
                    '@p67-cli/workspace/templates/hitl/src/index.ts.src',
                    { with: { type: 'file' } }
                )
            ).default;
            expect(typeof ref).toBe('string');
            expect(ref.length).toBeGreaterThan(0);
        });

        test('hitl manifest.yaml.src should be resolvable', async () => {
            const ref = (
                await import(
                    '@p67-cli/workspace/templates/hitl/manifest.yaml.src',
                    { with: { type: 'file' } }
                )
            ).default;
            expect(typeof ref).toBe('string');
            expect(ref.length).toBeGreaterThan(0);
        });
    });
});
