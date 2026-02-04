import { existsSync } from 'node:fs';
import { cp, mkdir } from 'node:fs/promises';
import { dirname, join } from 'node:path';
// TypeScript-specific boilerplate files
import tsLearnWorkflow from '@p67-cli/workspace/boiler-plate/LEARN_WORKFLOW.md.src' with {
    type: 'file',
};
import packagejson from '@p67-cli/workspace/boiler-plate/package.json.src' with {
    type: 'file',
};
import indexts from '@p67-cli/workspace/boiler-plate/src/index.ts.src' with {
    type: 'file',
};
import tsconfigjson from '@p67-cli/workspace/boiler-plate/tsconfig.json.src' with {
    type: 'file',
};
// Common boilerplate files (shared between languages)
import gitignore from '@p67-cli/workspace/boiler-plate-common/.gitignore.src' with {
    type: 'file',
};
import workflowGraphSchema from '@p67-cli/workspace/boiler-plate-common/conf/workflow_graph_schema.json.src' with {
    type: 'file',
};
import manifestyaml from '@p67-cli/workspace/boiler-plate-common/manifest.yaml.src' with {
    type: 'file',
};
// Python-specific boilerplate files
import pythonLearnWorkflow from '@p67-cli/workspace/boiler-plate-python/LEARN_WORKFLOW.md.src' with {
    type: 'file',
};
import pythonRequirementstxt from '@p67-cli/workspace/boiler-plate-python/requirements.txt.src' with {
    type: 'file',
};
import pythonMainpy from '@p67-cli/workspace/boiler-plate-python/src/main.py.src' with {
    type: 'file',
};
// @ts-expect-error - Bun's with { type: 'file' } returns a file path string
import sdksrc from '@workflow-sdk/index.ts' with { type: 'file' };
import { file } from 'bun';

export type WorkflowLanguage = 'typescript' | 'python';

// Files shared by all languages
const commonFiles: Record<string, string> = {
    [gitignore]: '.gitignore',
    [manifestyaml]: 'manifest.yaml',
    [workflowGraphSchema]: 'conf/workflow_graph_schema.json',
};

// TypeScript-specific files
const typescriptFiles: Record<string, string> = {
    [indexts]: 'src/index.ts',
    [sdksrc]: 'src/sdk.ts',
    [packagejson]: 'package.json',
    [tsconfigjson]: 'tsconfig.json',
    [tsLearnWorkflow]: 'LEARN_WORKFLOW.md',
};

// Python-specific files
const pythonFiles: Record<string, string> = {
    [pythonMainpy]: 'src/main.py',
    [pythonRequirementstxt]: 'requirements.txt',
    [pythonLearnWorkflow]: 'LEARN_WORKFLOW.md',
};

export class Workspace {
    private projectDir: string;
    private language: WorkflowLanguage;

    constructor(projectDir: string, language: WorkflowLanguage = 'typescript') {
        this.projectDir = projectDir;
        this.language = language;
    }

    async bootstrap() {
        await this.ensureSrcDirExists();

        // Copy common files for all languages
        for (const [key, value] of Object.entries(commonFiles)) {
            const outPath = join(this.projectDir, value);
            const outDir = dirname(outPath);
            await mkdir(outDir, { recursive: true });
            await this.materialize(key, outPath);
        }

        // Copy language-specific files
        const langFiles =
            this.language === 'python' ? pythonFiles : typescriptFiles;
        for (const [key, value] of Object.entries(langFiles)) {
            const outPath = join(this.projectDir, value);
            const outDir = dirname(outPath);
            await mkdir(outDir, { recursive: true });
            await this.materialize(key, outPath);
        }

        // For Python projects, copy the SDK stubs for IDE support
        if (this.language === 'python') {
            await this.copyPythonSdk();
        }
    }

    /**
     * Copy the Python SDK stubs to the project for IDE/VSCode support.
     * The stubs contain only type signatures and docstrings, not implementation.
     * The actual SDK is bundled at build time by 'p67 build'.
     */
    private async copyPythonSdk() {
        // In compiled Bun binaries, process.argv[0] and Bun.main return virtual paths (/$bunfs/root).
        // Use process.execPath which returns the actual path to the compiled binary.
        const binaryPath = process.execPath;
        const binaryDir = dirname(binaryPath);

        let sdkDir: string | null = null;
        let currentDir = binaryDir;

        // Walk up from the binary location to find the packages directory
        // Look for the stubs directory (interface-only, no implementation)
        for (let i = 0; i < 10; i++) {
            const candidateSdk = join(
                currentDir,
                'packages',
                'workflow-sdk-python',
                'p67_sdk_stubs',
            );
            if (existsSync(candidateSdk)) {
                sdkDir = candidateSdk;
                break;
            }
            const parent = dirname(currentDir);
            if (parent === currentDir) break; // Hit filesystem root
            currentDir = parent;
        }

        if (sdkDir) {
            // Copy stubs to p67_sdk/ so imports work correctly
            const sdkDestDir = join(this.projectDir, 'p67_sdk');
            await cp(sdkDir, sdkDestDir, { recursive: true });
            console.log('✔︎ Copied p67_sdk stubs for IDE support');
        } else {
            console.warn('⚠ Could not find p67_sdk stubs for IDE support');
        }
    }

    async materialize(ref: string, outPath: string) {
        const src = await file(ref).text();
        await Bun.write(outPath, src);
    }

    get srcDir(): string {
        return join(this.projectDir, 'src');
    }

    async ensureSrcDirExists() {
        await mkdir(this.srcDir, { recursive: true });
    }
}
