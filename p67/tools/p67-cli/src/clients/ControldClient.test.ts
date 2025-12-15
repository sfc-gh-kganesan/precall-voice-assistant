import { test, expect, mock, beforeEach, describe } from 'bun:test';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import type {
  HealthResponse,
  WorkflowCreateResponse,
  WorkflowListResponse,
  WorkflowRunResponse,
  ErrorResponse,
} from '@p67-cli/clients/ControldClient.ts';

describe('ControldClient', () => {
  let client: ControldClient;
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    client = new ControldClient({ baseUrl: 'http://localhost:3002', pat: 'test-pat' });
    originalFetch = globalThis.fetch;
  });

  describe('constructor', () => {
    test('should initialize with baseUrl and default timeout', () => {
      const client = new ControldClient({ baseUrl: 'http://localhost:3002', pat: 'test-pat' });
      expect(client).toBeDefined();
      expect(client.baseUrl).toBe('http://localhost:3002');
      expect(client.timeout).toBe(30000);
    });

    test('should strip trailing slash from baseUrl', () => {
      const client = new ControldClient({ baseUrl: 'http://localhost:3002/', pat: 'test-pat' });
      expect(client).toBeDefined();
      expect(client.baseUrl).toBe('http://localhost:3002');
    });

    test('should accept custom timeout', () => {
      const client = new ControldClient({
        baseUrl: 'http://localhost:3002',
        pat: 'test-pat',
        timeout: 60000,
      });
      expect(client).toBeDefined();
      expect(client.baseUrl).toBe('http://localhost:3002');
      expect(client.timeout).toBe(60000);
    });
  });

  describe('health()', () => {
    test('should return health status on success', async () => {
      const mockResponse: HealthResponse = {
        status: 'ok',
        timestamp: '2025-12-12T10:00:00.000Z',
        localStoragePath: '/tmp/storage',
      };

      globalThis.fetch = mock(async () => {
        return new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }) as unknown as typeof globalThis.fetch;

      const result = await client.health();

      expect(result).toEqual(mockResponse);
      expect(globalThis.fetch).toHaveBeenCalledWith(
        'http://localhost:3002/api/health',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            Authorization: 'Snowflake Token="test-pat"',
          }),
        }),
      );

      globalThis.fetch = originalFetch;
    });

    test('should throw error on failure', async () => {
      const mockError: ErrorResponse = {
        error: 'Service unavailable',
        message: 'Health check failed',
      };

      globalThis.fetch = mock(async () => {
        return new Response(JSON.stringify(mockError), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        });
      }) as unknown as typeof globalThis.fetch;

      await expect(client.health()).rejects.toThrow('Health check failed');

      globalThis.fetch = originalFetch;
    });

    test('should throw error with error field when message is not present', async () => {
      const mockError: ErrorResponse = {
        error: 'Service error',
      };

      globalThis.fetch = mock(async () => {
        return new Response(JSON.stringify(mockError), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        });
      }) as unknown as typeof globalThis.fetch;

      await expect(client.health()).rejects.toThrow('Service error');

      globalThis.fetch = originalFetch;
    });
  });

  describe('createWorkflow()', () => {
    test('should create workflow with File object', async () => {
      const mockResponse: WorkflowCreateResponse = {
        workflowId: 'wf-123e4567-e89b-12d3-a456-426614174000',
      };

      const mockFile = new File(['test content'], 'workflow.zip', {
        type: 'application/zip',
      });

      globalThis.fetch = mock(async (url, options) => {
        expect(url).toBe('http://localhost:3002/api/workflow/create');
        expect(options?.method).toBe('POST');
        expect(options?.body).toBeInstanceOf(FormData);

        return new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }) as unknown as typeof globalThis.fetch;

      const result = await client.createWorkflow(mockFile);

      expect(result).toEqual(mockResponse);
      expect(globalThis.fetch).toHaveBeenCalled();

      globalThis.fetch = originalFetch;
    });

    test('should create workflow with Blob and custom filename', async () => {
      const mockResponse: WorkflowCreateResponse = {
        workflowId: 'wf-987e4567-e89b-12d3-a456-426614174000',
      };

      const mockBlob = new Blob(['test content'], { type: 'application/zip' });

      globalThis.fetch = mock(async (url, options) => {
        expect(url).toBe('http://localhost:3002/api/workflow/create');
        expect(options?.method).toBe('POST');
        expect(options?.body).toBeInstanceOf(FormData);

        return new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }) as unknown as typeof globalThis.fetch;

      const result = await client.createWorkflow(mockBlob, 'custom.zip');

      expect(result).toEqual(mockResponse);
      expect(globalThis.fetch).toHaveBeenCalled();

      globalThis.fetch = originalFetch;
    });

    test('should throw error on bad request', async () => {
      const mockError: ErrorResponse = {
        error: 'No file uploaded',
      };

      const mockFile = new File(['test content'], 'workflow.zip', {
        type: 'application/zip',
      });

      globalThis.fetch = mock(async () => {
        return new Response(JSON.stringify(mockError), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        });
      }) as unknown as typeof globalThis.fetch;

      await expect(client.createWorkflow(mockFile)).rejects.toThrow('No file uploaded');

      globalThis.fetch = originalFetch;
    });

    test('should throw error on server error', async () => {
      const mockError: ErrorResponse = {
        error: 'Internal server error',
        message: 'Failed to process file',
      };

      const mockFile = new File(['test content'], 'workflow.zip', {
        type: 'application/zip',
      });

      globalThis.fetch = mock(async () => {
        return new Response(JSON.stringify(mockError), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        });
      }) as unknown as typeof globalThis.fetch;

      await expect(client.createWorkflow(mockFile)).rejects.toThrow('Failed to process file');

      globalThis.fetch = originalFetch;
    });
  });

  describe('listWorkflows()', () => {
    test('should return list of workflows', async () => {
      const mockResponse: WorkflowListResponse = {
        workflows: ['wf-123', 'wf-456', 'wf-789'],
      };

      globalThis.fetch = mock(async () => {
        return new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }) as unknown as typeof globalThis.fetch;

      const result = await client.listWorkflows();

      expect(result).toEqual(mockResponse);
      expect(result.workflows).toHaveLength(3);
      expect(globalThis.fetch).toHaveBeenCalledWith(
        'http://localhost:3002/api/workflow/list',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            Authorization: 'Snowflake Token="test-pat"',
          }),
        }),
      );

      globalThis.fetch = originalFetch;
    });

    test('should return empty array when no workflows exist', async () => {
      const mockResponse: WorkflowListResponse = {
        workflows: [],
      };

      globalThis.fetch = mock(async () => {
        return new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }) as unknown as typeof globalThis.fetch;

      const result = await client.listWorkflows();

      expect(result).toEqual(mockResponse);
      expect(result.workflows).toHaveLength(0);

      globalThis.fetch = originalFetch;
    });

    test('should throw error on server error', async () => {
      const mockError: ErrorResponse = {
        error: 'Internal server error',
        message: 'Failed to list workflows',
      };

      globalThis.fetch = mock(async () => {
        return new Response(JSON.stringify(mockError), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        });
      }) as unknown as typeof globalThis.fetch;

      await expect(client.listWorkflows()).rejects.toThrow('Failed to list workflows');

      globalThis.fetch = originalFetch;
    });
  });

  describe('runWorkflow()', () => {
    test('should execute workflow successfully', async () => {
      const mockResponse: WorkflowRunResponse = {
        exitCode: 0,
        stdout: 'Task completed successfully',
        stderr: '',
        success: true,
      };

      const workflowId = 'wf-123e4567-e89b-12d3-a456-426614174000';

      globalThis.fetch = mock(async (url) => {
        expect(url).toBe(`http://localhost:3002/api/workflow/${workflowId}/run`);

        return new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }) as unknown as typeof globalThis.fetch;

      const result = await client.runWorkflow(workflowId);

      expect(result).toEqual(mockResponse);
      expect(result.success).toBe(true);
      expect(result.exitCode).toBe(0);

      globalThis.fetch = originalFetch;
    });

    test('should return failure response when workflow fails', async () => {
      const mockResponse: WorkflowRunResponse = {
        exitCode: 1,
        stdout: 'Some output',
        stderr: 'Error occurred',
        success: false,
      };

      const workflowId = 'wf-123e4567-e89b-12d3-a456-426614174000';

      globalThis.fetch = mock(async () => {
        return new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }) as unknown as typeof globalThis.fetch;

      const result = await client.runWorkflow(workflowId);

      expect(result).toEqual(mockResponse);
      expect(result.success).toBe(false);
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toBe('Error occurred');

      globalThis.fetch = originalFetch;
    });

    test('should throw error when workflow not found', async () => {
      const mockError: ErrorResponse = {
        error: 'Invalid request',
        message: 'Workflow wf-invalid does not exist',
      };

      globalThis.fetch = mock(async () => {
        return new Response(JSON.stringify(mockError), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        });
      }) as unknown as typeof globalThis.fetch;

      expect(client.runWorkflow('wf-invalid')).rejects.toThrow(
        'Workflow wf-invalid does not exist',
      );

      globalThis.fetch = originalFetch;
    });

    test('should call correct endpoint with workflow ID in path', async () => {
      const mockResponse: WorkflowRunResponse = {
        exitCode: 0,
        stdout: 'Success',
        stderr: '',
        success: true,
      };

      const workflowId = 'wf-custom-id-123';

      globalThis.fetch = mock(async (url, options) => {
        expect(url).toBe(`http://localhost:3002/api/workflow/${workflowId}/run`);
        expect(options?.method).toBe('POST');
        expect(options?.headers).toEqual(
          expect.objectContaining({
            Authorization: 'Snowflake Token="test-pat"',
          }),
        );

        return new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }) as unknown as typeof globalThis.fetch;

      await client.runWorkflow(workflowId);

      expect(globalThis.fetch).toHaveBeenCalled();

      globalThis.fetch = originalFetch;
    });
  });
});
