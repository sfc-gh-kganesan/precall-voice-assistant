import { mkdir } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import gitignore from '@p67-cli/workspace/boiler-plate/.gitignore.src' with {
    type: 'file',
};
import workflowGraphSchema from '@p67-cli/workspace/boiler-plate/conf/workflow_graph_schema.json.src' with {
    type: 'file',
};
import learnWorkflow from '@p67-cli/workspace/boiler-plate/LEARN_WORKFLOW.md.src' with {
    type: 'file',
};
import manifestyaml from '@p67-cli/workspace/boiler-plate/manifest.yaml.src' with {
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
// @ts-expect-error - Bun's with { type: 'file' } returns a file path string
import sdksrc from '@workflow-sdk/index.ts' with { type: 'file' };
import { file } from 'bun';

const files: Record<string, string> = {
    [gitignore]: '.gitignore',
    [indexts]: 'src/index.ts',
    [sdksrc]: 'src/sdk.ts',
    [packagejson]: 'package.json',
    [tsconfigjson]: 'tsconfig.json',
    [manifestyaml]: 'manifest.yaml',
    [learnWorkflow]: 'LEARN_WORKFLOW.md',
    [workflowGraphSchema]: 'conf/workflow_graph_schema.json',
};

export class Workspace {
    private projectDir: string;

    constructor(projectDir: string) {
        this.projectDir = projectDir;
    }

    async bootstrap() {
        await this.ensureSrcDirExists();
        for (const [key, value] of Object.entries(files)) {
            const outPath = join(this.projectDir, value);
            const outDir = dirname(outPath);
            await mkdir(outDir, { recursive: true });
            this.materialize(key, join(this.projectDir, value));
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
