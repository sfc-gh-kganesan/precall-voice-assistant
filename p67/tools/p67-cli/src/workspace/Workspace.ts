import { mkdir } from 'node:fs/promises';
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
// TODO: Templates are agent-generated stubs. hello-world doesn't use the P67 SDK at all,
// hitl has untyped sdk param. Both should demonstrate real P67 features (sdk.sql,
// sdk.complete, Cortex AI, secrets). See templates/ directory.
import helloWorldManifest from '@p67-cli/workspace/templates/hello-world/manifest.yaml.src' with {
    type: 'file',
};
// Template: hello-world
import helloWorldIndexTs from '@p67-cli/workspace/templates/hello-world/src/index.ts.src' with {
    type: 'file',
};
import hitlManifest from '@p67-cli/workspace/templates/hitl/manifest.yaml.src' with {
    type: 'file',
};
// Template: hitl
import hitlIndexTs from '@p67-cli/workspace/templates/hitl/src/index.ts.src' with {
    type: 'file',
};
import mcpClientManifest from '@p67-cli/workspace/templates/mcp-client/manifest.yaml.src' with {
    type: 'file',
};
import mcpClientPackageJson from '@p67-cli/workspace/templates/mcp-client/package.json.src' with {
    type: 'file',
};
import mcpClientRequirementsTxt from '@p67-cli/workspace/templates/mcp-client/requirements.txt.src' with {
    type: 'file',
};
// Template: mcp-client (TypeScript)
import mcpClientIndexTs from '@p67-cli/workspace/templates/mcp-client/src/index.ts.src' with {
    type: 'file',
};
// Template: mcp-client (Python)
import mcpClientMainPy from '@p67-cli/workspace/templates/mcp-client/src/main.py.src' with {
    type: 'file',
};
// @ts-expect-error - Bun's with { type: 'file' } returns a file path string
import sdksrc from '@workflow-sdk/index.ts' with { type: 'file' };
// Python SDK full implementation (for p67 build — bundled with workflow)
// @ts-expect-error - Bun's with { type: 'file' } returns a file path string
import pySdkInit from '@workflow-sdk-python/p67_sdk/__init__.py' with {
    type: 'file',
};
// @ts-expect-error - Bun's with { type: 'file' } returns a file path string
import pySdkIpc from '@workflow-sdk-python/p67_sdk/ipc.py' with {
    type: 'file',
};
// @ts-expect-error - Bun's with { type: 'file' } returns a file path string
import pySdkSdk from '@workflow-sdk-python/p67_sdk/sdk.py' with {
    type: 'file',
};
// @ts-expect-error - Bun's with { type: 'file' } returns a file path string
import pySdkTypes from '@workflow-sdk-python/p67_sdk/types.py' with {
    type: 'file',
};
// Python SDK stubs (for p67 init — IDE/type-checking support)
// @ts-expect-error - Bun's with { type: 'file' } returns a file path string
import pyStubInit from '@workflow-sdk-python/p67_sdk_stubs/__init__.py' with {
    type: 'file',
};
// @ts-expect-error - Bun's with { type: 'file' } returns a file path string
import pyStubSdk from '@workflow-sdk-python/p67_sdk_stubs/sdk.py' with {
    type: 'file',
};
// @ts-expect-error - Bun's with { type: 'file' } returns a file path string
import pyStubTypes from '@workflow-sdk-python/p67_sdk_stubs/types.py' with {
    type: 'file',
};
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

// Python SDK stubs — written to project by p67 init for IDE support
const pythonStubFiles: Record<string, string> = {
    [pyStubInit]: 'p67_sdk/__init__.py',
    [pyStubSdk]: 'p67_sdk/sdk.py',
    [pyStubTypes]: 'p67_sdk/types.py',
};

// Python SDK full implementation — bundled with workflow by p67 build
export const pythonSdkFiles: Record<string, string> = {
    [pySdkInit]: '__init__.py',
    [pySdkSdk]: 'sdk.py',
    [pySdkTypes]: 'types.py',
    [pySdkIpc]: 'ipc.py',
};

// Python-specific files
const pythonFiles: Record<string, string> = {
    [pythonMainpy]: 'src/main.py',
    [pythonRequirementstxt]: 'requirements.txt',
    [pythonLearnWorkflow]: 'LEARN_WORKFLOW.md',
};

// Template-specific files (only the files that differ from default boilerplate).
// `common` files apply to all languages. `typescript` / `python` files are
// copied only when that language is selected and override the corresponding
// boilerplate file.
interface TemplateEntry {
    common: Record<string, string>;
    typescript?: Record<string, string>;
    python?: Record<string, string>;
}

const templateFiles: Record<string, TemplateEntry> = {
    'hello-world': {
        common: {
            [helloWorldManifest]: 'manifest.yaml',
        },
        typescript: {
            [helloWorldIndexTs]: 'src/index.ts',
        },
    },
    hitl: {
        common: {
            [hitlManifest]: 'manifest.yaml',
        },
        typescript: {
            [hitlIndexTs]: 'src/index.ts',
        },
    },
    'mcp-client': {
        common: {
            [mcpClientManifest]: 'manifest.yaml',
        },
        typescript: {
            [mcpClientIndexTs]: 'src/index.ts',
            [mcpClientPackageJson]: 'package.json',
        },
        python: {
            [mcpClientMainPy]: 'src/main.py',
            [mcpClientRequirementsTxt]: 'requirements.txt',
        },
    },
};

export function listTemplates(): string[] {
    return Object.keys(templateFiles);
}

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

    async bootstrapTemplate(templateName: string) {
        const tmplEntry = templateFiles[templateName];
        if (!tmplEntry) {
            throw new Error(
                `Unknown template "${templateName}". Available templates: ${listTemplates().join(', ')}`,
            );
        }

        await this.ensureSrcDirExists();

        // Collect all output paths that the template will provide so we can
        // skip the corresponding boilerplate files (common + language-specific).
        const langKey = this.language === 'python' ? 'python' : 'typescript';
        const langOverrides = tmplEntry[langKey] ?? {};
        const allTemplateOutputPaths = new Set([
            ...Object.values(tmplEntry.common),
            ...Object.values(langOverrides),
        ]);

        // Copy common boilerplate files, skipping any that the template overrides
        for (const [key, value] of Object.entries(commonFiles)) {
            if (allTemplateOutputPaths.has(value)) continue;
            const outPath = join(this.projectDir, value);
            const outDir = dirname(outPath);
            await mkdir(outDir, { recursive: true });
            await this.materialize(key, outPath);
        }

        // Copy language-specific boilerplate, skipping template overrides
        const langFiles =
            this.language === 'python' ? pythonFiles : typescriptFiles;
        for (const [key, value] of Object.entries(langFiles)) {
            if (allTemplateOutputPaths.has(value)) continue;
            const outPath = join(this.projectDir, value);
            const outDir = dirname(outPath);
            await mkdir(outDir, { recursive: true });
            await this.materialize(key, outPath);
        }

        // Copy template files: common first, then language-specific
        for (const files of [tmplEntry.common, langOverrides]) {
            for (const [key, value] of Object.entries(files)) {
                const outPath = join(this.projectDir, value);
                const outDir = dirname(outPath);
                await mkdir(outDir, { recursive: true });
                await this.materialize(key, outPath);
            }
        }

        // For Python projects, copy the SDK stubs for IDE support
        if (this.language === 'python') {
            await this.copyPythonSdk();
        }
    }

    /**
     * Copy the Python SDK stubs to the project for IDE/VSCode support.
     * The stubs are embedded in the binary at compile time, so this works
     * whether running from the repo or from a standalone installed binary.
     */
    private async copyPythonSdk() {
        for (const [ref, relPath] of Object.entries(pythonStubFiles)) {
            const outPath = join(this.projectDir, relPath);
            const outDir = dirname(outPath);
            await mkdir(outDir, { recursive: true });
            await this.materialize(ref, outPath);
        }
        console.log('✔︎ Copied p67_sdk stubs for IDE support');
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
