import { describe, expect, it } from 'vitest';
import {
    MessageSchema,
    MessageType,
    makeRunWorkflowMessage,
    makeThrowErrorMessage,
    RunWorkflowMessageSchema,
    type SerializedP67Config,
    WorkflowError,
    WorkflowErrorMessageSchema,
} from './schema.js';

// Test helper: minimal valid config
const testConfig: SerializedP67Config = {
    snowflakeConfig: {},
    parameters: {},
};

describe('runtime/schema', () => {
    describe('MessageType enum', () => {
        it('should have RunWorkflow type', () => {
            expect(MessageType.RunWorkflow).toBe('RunWorkflow');
        });

        it('should have ThrowError type', () => {
            expect(MessageType.ThrowError).toBe('ThrowError');
        });
    });

    describe('WorkflowError enum', () => {
        it('should have all error types', () => {
            expect(WorkflowError.ExecutionError).toBe('ExecutionError');
            expect(WorkflowError.IndexScriptImportError).toBe(
                'IndexScriptImportError',
            );
            expect(WorkflowError.IndexScriptInvalidContents).toBe(
                'IndexScriptInvalidContents',
            );
            expect(WorkflowError.IndexScriptNotFound).toBe(
                'IndexScriptNotFound',
            );
            expect(WorkflowError.ManifestLoadParseError).toBe(
                'ManifestLoadParseError',
            );
            expect(WorkflowError.ManifestNotFound).toBe('ManifestNotfound');
            expect(WorkflowError.MessageInvalidContents).toBe(
                'MessageInvalidContents',
            );
            expect(WorkflowError.MessageInvalidType).toBe('MessageInvalidType');
        });
    });

    describe('makeRunWorkflowMessage', () => {
        it('should create a RunWorkflow message with correct type', () => {
            const message = makeRunWorkflowMessage({
                dir: '/path/to/workflow',
                config: testConfig,
            });

            expect(message.type).toBe(MessageType.RunWorkflow);
            expect(message.dir).toBe('/path/to/workflow');
            expect(message.config).toEqual(testConfig);
        });

        it('should create valid message that passes schema validation', () => {
            const message = makeRunWorkflowMessage({
                dir: '/test/dir',
                config: testConfig,
            });
            const result = RunWorkflowMessageSchema.safeParse(message);

            expect(result.success).toBe(true);
        });
    });

    describe('makeThrowErrorMessage', () => {
        it('should create a ThrowError message with correct type', () => {
            const message = makeThrowErrorMessage({
                error: WorkflowError.ExecutionError,
                message: 'Something went wrong',
            });

            expect(message.type).toBe(MessageType.ThrowError);
            expect(message.error).toBe(WorkflowError.ExecutionError);
            expect(message.message).toBe('Something went wrong');
        });

        it('should create valid message that passes schema validation', () => {
            const message = makeThrowErrorMessage({
                error: WorkflowError.IndexScriptNotFound,
                message: 'Script not found',
            });
            const result = WorkflowErrorMessageSchema.safeParse(message);

            expect(result.success).toBe(true);
        });
    });

    describe('RunWorkflowMessageSchema', () => {
        it('should validate correct RunWorkflow message', () => {
            const message = {
                type: MessageType.RunWorkflow,
                dir: '/workflow/path',
                config: testConfig,
            };
            const result = RunWorkflowMessageSchema.safeParse(message);

            expect(result.success).toBe(true);
        });

        it('should reject message with missing dir', () => {
            const message = {
                type: MessageType.RunWorkflow,
                config: testConfig,
            };
            const result = RunWorkflowMessageSchema.safeParse(message);

            expect(result.success).toBe(false);
        });

        it('should reject message with missing config', () => {
            const message = {
                type: MessageType.RunWorkflow,
                dir: '/workflow/path',
            };
            const result = RunWorkflowMessageSchema.safeParse(message);

            expect(result.success).toBe(false);
        });

        it('should reject message with wrong type', () => {
            const message = {
                type: MessageType.ThrowError,
                dir: '/workflow/path',
                config: testConfig,
            };
            const result = RunWorkflowMessageSchema.safeParse(message);

            expect(result.success).toBe(false);
        });

        it('should reject message with invalid dir type', () => {
            const message = {
                type: MessageType.RunWorkflow,
                dir: 123,
                config: testConfig,
            };
            const result = RunWorkflowMessageSchema.safeParse(message);

            expect(result.success).toBe(false);
        });
    });

    describe('WorkflowErrorMessageSchema', () => {
        it('should validate correct ThrowError message', () => {
            const message = {
                type: MessageType.ThrowError,
                error: WorkflowError.ExecutionError,
                message: 'Error details',
            };
            const result = WorkflowErrorMessageSchema.safeParse(message);

            expect(result.success).toBe(true);
        });

        it('should reject message with missing error field', () => {
            const message = {
                type: MessageType.ThrowError,
                message: 'Error details',
            };
            const result = WorkflowErrorMessageSchema.safeParse(message);

            expect(result.success).toBe(false);
        });

        it('should reject message with missing message field', () => {
            const message = {
                type: MessageType.ThrowError,
                error: WorkflowError.ExecutionError,
            };
            const result = WorkflowErrorMessageSchema.safeParse(message);

            expect(result.success).toBe(false);
        });

        it('should reject message with invalid error enum value', () => {
            const message = {
                type: MessageType.ThrowError,
                error: 'InvalidErrorType',
                message: 'Error details',
            };
            const result = WorkflowErrorMessageSchema.safeParse(message);

            expect(result.success).toBe(false);
        });

        it('should validate all WorkflowError enum values', () => {
            const errorTypes = Object.values(WorkflowError);

            for (const errorType of errorTypes) {
                const message = {
                    type: MessageType.ThrowError,
                    error: errorType,
                    message: `Test error: ${errorType}`,
                };
                const result = WorkflowErrorMessageSchema.safeParse(message);

                expect(result.success).toBe(true);
            }
        });
    });

    describe('MessageSchema (discriminated union)', () => {
        it('should validate RunWorkflow message', () => {
            const message = {
                type: MessageType.RunWorkflow,
                dir: '/test/path',
                config: testConfig,
            };
            const result = MessageSchema.safeParse(message);

            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.type).toBe(MessageType.RunWorkflow);
            }
        });

        it('should validate ThrowError message', () => {
            const message = {
                type: MessageType.ThrowError,
                error: WorkflowError.ExecutionError,
                message: 'Test error',
            };
            const result = MessageSchema.safeParse(message);

            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.type).toBe(MessageType.ThrowError);
            }
        });

        it('should reject message with unknown type', () => {
            const message = {
                type: 'UnknownType',
                data: 'some data',
            };
            const result = MessageSchema.safeParse(message);

            expect(result.success).toBe(false);
        });

        it('should reject message with missing type', () => {
            const message = {
                dir: '/test/path',
            };
            const result = MessageSchema.safeParse(message);

            expect(result.success).toBe(false);
        });

        it('should reject null', () => {
            const result = MessageSchema.safeParse(null);

            expect(result.success).toBe(false);
        });

        it('should reject undefined', () => {
            const result = MessageSchema.safeParse(undefined);

            expect(result.success).toBe(false);
        });

        it('should reject empty object', () => {
            const result = MessageSchema.safeParse({});

            expect(result.success).toBe(false);
        });

        it('should reject primitive values', () => {
            expect(MessageSchema.safeParse('string').success).toBe(false);
            expect(MessageSchema.safeParse(123).success).toBe(false);
            expect(MessageSchema.safeParse(true).success).toBe(false);
        });
    });
});
