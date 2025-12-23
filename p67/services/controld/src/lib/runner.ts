import { fork } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export type RunResult = {
	stdout: string;
	stderr: string;
	exitCode: number;
};

export interface ExecuteMessage {
	dir: string;
	action: 'run';
}

export class Runner {
	constructor(private readonly workflowDir: string) {}

	public async start(): Promise<RunResult> {
		console.log(`Running workflow from ${this.workflowDir}...`);
		const __filename = fileURLToPath(import.meta.url);
		const __dirname = dirname(__filename);
		const hostPath = resolve(__dirname, 'runner-host.js');

		const proc = fork(hostPath, [], {
			stdio: ['pipe', 'pipe', 'pipe', 'ipc'],
		});

		let output = '';
		let errorOutput = '';

		if (proc.stdout) {
			proc.stdout.on('data', (data: Buffer) => {
				const text = data.toString();
				console.log('[Child stdout]:', text);
				output += text;
			});
		}

		if (proc.stderr) {
			proc.stderr.on('data', (data: Buffer) => {
				const text = data.toString();
				console.error('[Child stderr]:', text);
				errorOutput += text;
			});
		}

		proc.on('message', (message) => {
			console.log('main received from child: ', message);
		});

		proc.on('error', (error) => {
			console.error('child process error:', error);
		});

		proc.on('exit', (code) => {
			console.log(`Child process exited with code ${code}`);
		});

		const m: ExecuteMessage = {
			dir: this.workflowDir,
			action: 'run',
		};

		proc.send(m);

		const exitCode = await new Promise<number>((resolve) => {
			proc.on('exit', (code) => {
				resolve(code || 0);
			});

			proc.on('error', (err) => {
				console.error('[Child process error]:', err);
				resolve(1);
			});
		});

		console.log(output);
		console.error(errorOutput);
		console.log(`Runner process exited with code ${exitCode}`);

		return {
			stdout: output,
			stderr: errorOutput,
			exitCode,
		};
	}
}
