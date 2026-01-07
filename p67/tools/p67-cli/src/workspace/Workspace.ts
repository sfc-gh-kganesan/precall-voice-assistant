import { mkdir } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import gitignore from '@p67-cli/workspace/boiler-plate/.gitignore.src' with {
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
import { file } from 'bun';

const files: Record<string, string> = {
    [gitignore]: '.gitignore',
    [indexts]: 'src/index.ts',
    [packagejson]: 'package.json',
    [tsconfigjson]: 'tsconfig.json',
    [manifestyaml]: 'manifest.yaml',
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

    get sdkFilePath(): string {
        return join(this.srcDir, 'sdk.js');
    }

    async ensureSrcDirExists() {
        await mkdir(this.srcDir, { recursive: true });
    }
}
