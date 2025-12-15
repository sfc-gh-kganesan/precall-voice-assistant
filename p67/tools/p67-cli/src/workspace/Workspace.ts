import sdkBundle from '@agent-sdk/dist/bundle.src' with { type: 'file' };
import indexts from '@p67-cli/workspace/boiler-plate/src/index.ts.src' with { type: 'file' };
import buildjs from '@p67-cli/workspace/boiler-plate/build.js.src' with { type: 'file' };
import packagejson from '@p67-cli/workspace/boiler-plate/package.json.src' with { type: 'file' };
import tsconfigjson from '@p67-cli/workspace/boiler-plate/tsconfig.json.src' with { type: 'file' };
import { mkdir } from 'node:fs/promises';
import { file } from 'bun';
import { join, dirname } from 'path';

const files: Record<string, string> = {
  [sdkBundle]: 'src/sdk.js',
  [indexts]: 'src/index.ts',
  [buildjs]: 'build.js',
  [packagejson]: 'package.json',
  [tsconfigjson]: 'tsconfig.json',
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
