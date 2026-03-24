/**
 * Runtime Adapter
 *
 * Provides a unified interface for spawning and communicating with
 * workflow runtime hosts across different environments:
 *
 * - DockerAdapter: local dev, uses `docker run -i` with stdin/stdout NDJSON
 * - SPCSAdapter: Snowpark Container Services, uses EXECUTE JOB SERVICE + stage I/O
 */

import type { ChildProcess } from 'node:child_process';
import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import type { SandboxConfig } from '@controld/config.js';
import type { Message } from '@controld/lib/runtime/schema.js';

export type WorkflowLanguage = 'typescript' | 'python';

/**
 * Interface for runtime adapters that handle language-specific
 * process spawning and IPC via stdin/stdout (Docker-local mode).
 */
export interface RuntimeAdapter {
    /** The language this adapter handles */
    readonly language: WorkflowLanguage;

    /** Spawn the runtime host process */
    spawn(workflowDir?: string): ChildProcess;

    /** Send a message to the child process */
    sendMessage(proc: ChildProcess, message: Message): void;

    /** Set up message handling from the child process */
    onMessage(proc: ChildProcess, handler: (msg: Message) => void): void;
}

/**
 * Shared NDJSON-over-stdout message handling for adapters that
 * communicate via stdin/stdout.
 */
class NdjsonMessageHandler {
    private messageBuffer: Map<ChildProcess, string> = new Map();

    sendMessage(proc: ChildProcess, message: Message): void {
        if (proc.stdin) {
            proc.stdin.write(`${JSON.stringify(message)}\n`);
        }
    }

    onMessage(
        proc: ChildProcess,
        handler: (msg: Message) => void,
        label: string,
    ): void {
        if (!proc.stdout) return;

        this.messageBuffer.set(proc, '');

        proc.stdout.on('data', (data: Buffer) => {
            let buffer = this.messageBuffer.get(proc) || '';
            buffer += data.toString();

            const lines = buffer.split('\n');
            this.messageBuffer.set(proc, lines.pop() || '');

            for (const line of lines) {
                if (!line.trim()) continue;

                try {
                    const msg = JSON.parse(line);
                    handler(msg as Message);
                } catch {
                    console.log(`[${label} stdout]:`, line);
                }
            }
        });

        proc.on('exit', () => {
            this.messageBuffer.delete(proc);
        });
    }
}

/**
 * Docker-based runtime adapter (Python + TypeScript).
 * Runs the p67-runner container with the workflow directory bind-mounted.
 * The Go supervisor inside the container auto-detects the language
 * (main.py vs index.js) and execs the appropriate host process.
 * IPC is NDJSON over stdin/stdout for both languages.
 */
export class DockerAdapter implements RuntimeAdapter {
    readonly language: WorkflowLanguage;

    private readonly ndjson = new NdjsonMessageHandler();

    constructor(
        language: WorkflowLanguage,
        private readonly image: string,
        private readonly hostStorageRoot?: string,
        private readonly containerStorageRoot?: string,
    ) {
        this.language = language;
    }

    spawn(workflowDir?: string): ChildProcess {
        if (!workflowDir) {
            throw new Error(
                'DockerAdapter requires workflowDir to be passed to spawn()',
            );
        }

        // Translate container path to host path for Docker bind mount
        let mountPath = workflowDir;
        if (this.hostStorageRoot && this.containerStorageRoot) {
            mountPath = workflowDir.replace(
                this.containerStorageRoot,
                this.hostStorageRoot,
            );
        }

        return spawn(
            'docker',
            [
                'run',
                '--rm',
                '-i',
                '-v',
                `${mountPath}:/workflow:ro`,
                this.image,
                '/workflow',
            ],
            { stdio: ['pipe', 'pipe', 'pipe'] },
        );
    }

    sendMessage(proc: ChildProcess, message: Message): void {
        this.ndjson.sendMessage(proc, message);
    }

    onMessage(proc: ChildProcess, handler: (msg: Message) => void): void {
        this.ndjson.onMessage(proc, handler, 'Docker');
    }
}

// ---------------------------------------------------------------------------
// SPCS (Snowpark Container Services) Adapter
// ---------------------------------------------------------------------------

/**
 * Result of an SPCS job execution.
 */
export type SPCSJobResult = {
    /** NDJSON messages emitted by the runner (read from stage) */
    messages: Message[];
    /** Container stderr (from SPCS_GET_LOGS) */
    stderr: string[];
    /** Exit status string from DESCRIBE SERVICE */
    status: string;
};

/**
 * SPCS-based runtime adapter.
 *
 * Unlike DockerAdapter (which relies on ChildProcess stdin/stdout pipes),
 * SPCSAdapter launches an ephemeral SPCS job service via EXECUTE JOB SERVICE.
 *
 * Communication flow:
 *   1. controld uploads workflow files to a Snowflake internal stage
 *   2. controld executes EXECUTE JOB SERVICE with an inline spec that
 *      mounts the stage as a volume at /workflow and mounts a results
 *      volume backed by the same stage at /results
 *   3. The p67-runner container reads /workflow as usual (no code changes)
 *   4. The host process writes NDJSON messages to /results/messages.ndjson
 *      (in SPCS mode, detected via P67_RESULTS_DIR env var)
 *   5. controld polls DESCRIBE SERVICE until the job finishes
 *   6. controld reads the results file from the stage
 */
export class SPCSAdapter {
    readonly language: WorkflowLanguage;
    private readonly image: string;
    private readonly computePool: string;
    private readonly warehouseName: string;
    private readonly stageName: string;

    constructor(
        language: WorkflowLanguage,
        config: Extract<SandboxConfig, { mode: 'spcs' }>,
    ) {
        this.language = language;
        this.image = config.runnerImage;
        this.computePool = config.computePool;
        this.warehouseName = config.warehouseName;
        this.stageName = config.stageName;
    }

    /**
     * Generate a unique job ID for this workflow run.
     */
    private jobId(): string {
        return `runner_${randomUUID().replace(/-/g, '').slice(0, 12)}`;
    }

    /**
     * Build the EXECUTE JOB SERVICE SQL statement.
     *
     * @param secrets Optional list of Snowflake SECRET objects to mount as env vars.
     *   Only used when SECRET_BACKEND=snowflake. SPCS reads the secret values and
     *   injects them into the container — controld never sees the plaintext.
     */
    buildJobServiceSQL(
        jobName: string,
        stagePath: string,
        runWorkflowMessage: Message,
        resourceRequests?: { cpu?: string; memory?: string },
        controldUrl?: string,
        secrets?: Array<{ objectName: string; envVarName: string }>,
    ): string {
        const cpu = resourceRequests?.cpu ?? '0.5';
        const memory = resourceRequests?.memory ?? '512Mi';
        const limitCpu = '1';
        const limitMemory = '1Gi';

        // The RunWorkflow message is passed as a base64-encoded env var.
        // The runner reads this instead of stdin in SPCS mode.
        const messageB64 = Buffer.from(
            JSON.stringify(runWorkflowMessage),
        ).toString('base64');

        // Results volume is stage-backed so controld can read messages.ndjson
        // after the job completes. The runner tees stdout to this file.
        const controldEnvLine = controldUrl
            ? `\n      P67_CONTROLD_URL: "${controldUrl}"`
            : '';

        // Build the secrets YAML block for Snowflake SECRET object mounting.
        // Each secret is mounted as an env var in the container by SPCS.
        let secretsBlock = '';
        if (secrets && secrets.length > 0) {
            const lines = secrets.map(
                (s) =>
                    `    - snowflakeSecret:\n        objectName: ${s.objectName}\n      secretKeyRef: secret_string\n      envVarName: ${s.envVarName}`,
            );
            secretsBlock = `\n    secrets:\n${lines.join('\n')}`;
        }

        const spec = `
spec:
  containers:
  - name: runner
    image: ${this.image}
    args:
    - "/workflow"
    env:
      P67_RUN_MESSAGE_B64: "${messageB64}"
      P67_RESULTS_DIR: "/results"${controldEnvLine}
    volumeMounts:
    - name: workflow-files
      mountPath: /workflow
    - name: results
      mountPath: /results
    resources:
      requests:
        cpu: "${cpu}"
        memory: "${memory}"
      limits:
        cpu: "${limitCpu}"
        memory: "${limitMemory}"${secretsBlock}
  volumes:
  - name: workflow-files
    source: "@${this.stageName}/${stagePath}"
    uid: 1000
    gid: 1000
  - name: results
    source: "@${this.stageName}/${stagePath}/results"
    uid: 1000
    gid: 1000
`.trim();

        return [
            `EXECUTE JOB SERVICE`,
            `  IN COMPUTE POOL ${this.computePool}`,
            `  NAME = ${jobName}`,
            `  QUERY_WAREHOUSE = ${this.warehouseName}`,
            `  EXTERNAL_ACCESS_INTEGRATIONS = (reference('google_oauth_eai'), reference('snowflake_egress_eai'), reference('postgres_eai'))`,
            `  FROM SPECIFICATION $$`,
            spec,
            `$$`,
        ].join('\n');
    }

    /**
     * Build SQL to upload workflow files to the stage.
     * Returns [putSQL, stagePath] where stagePath is the sub-directory on stage.
     */
    buildStageUploadSQL(
        jobName: string,
        workflowDir: string,
    ): { putSQL: string; stagePath: string } {
        const stagePath = jobName;
        const putSQL = `PUT 'file://${workflowDir}/*' '@${this.stageName}/${stagePath}/' AUTO_COMPRESS=FALSE OVERWRITE=TRUE`;
        return { putSQL, stagePath };
    }

    /**
     * Build SQL to poll job status.
     */
    buildDescribeSQL(jobName: string): string {
        return `CALL ${jobName}!SPCS_WAIT_FOR('DONE', 600)`;
    }

    /**
     * Build SQL to retrieve container logs.
     */
    buildGetLogsSQL(jobName: string): string {
        return `SELECT * FROM TABLE(${jobName}!SPCS_GET_LOGS())`;
    }

    /**
     * Build SQL to read the results NDJSON file from the stage.
     * The runner writes messages.ndjson to the results volume which is
     * backed by @stageName/stagePath/results/.
     */
    buildGetResultsSQL(stagePath: string): string {
        return `GET '@${this.stageName}/${stagePath}/results/messages.ndjson' 'file:///tmp/p67-results/'`;
    }

    /**
     * The local path where GET downloads the results file.
     */
    get resultsLocalPath(): string {
        return '/tmp/p67-results/messages.ndjson';
    }

    /**
     * Build SQL to clean up the job service.
     */
    buildCleanupSQL(jobName: string, stagePath: string): string[] {
        return [
            `DROP SERVICE IF EXISTS ${jobName}`,
            `REMOVE '@${this.stageName}/${stagePath}/'`,
        ];
    }

    /**
     * Create a new job ID.
     */
    createJobId(): string {
        return this.jobId();
    }
}

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

export type DockerAdapterConfig = Extract<SandboxConfig, { mode: 'docker' }>;
export type SPCSAdapterConfig = Extract<SandboxConfig, { mode: 'spcs' }>;

/**
 * Create a DockerAdapter for the given workflow language.
 */
export function createDockerAdapter(
    language: WorkflowLanguage,
    config: DockerAdapterConfig,
): DockerAdapter {
    return new DockerAdapter(
        language,
        config.runnerImage,
        config.hostStorageRoot,
        config.containerStorageRoot,
    );
}

/**
 * Create an SPCSAdapter for the given workflow language.
 */
export function createSPCSAdapter(
    language: WorkflowLanguage,
    config: SPCSAdapterConfig,
): SPCSAdapter {
    return new SPCSAdapter(language, config);
}

/**
 * Create the appropriate adapter based on sandbox config.
 * Returns DockerAdapter | SPCSAdapter (not a unified interface,
 * because SPCS fundamentally differs from the ChildProcess model).
 */
export function createAdapter(
    language: WorkflowLanguage,
    config: SandboxConfig,
): DockerAdapter | SPCSAdapter {
    if (config.mode === 'spcs') {
        return new SPCSAdapter(language, config);
    }
    return new DockerAdapter(
        language,
        config.runnerImage,
        config.hostStorageRoot,
        config.containerStorageRoot,
    );
}
