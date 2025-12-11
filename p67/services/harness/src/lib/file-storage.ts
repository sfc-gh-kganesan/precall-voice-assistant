import { join } from 'path';
import { mkdir, writeFile, readdir, readFile } from 'fs/promises';
import { existsSync } from 'fs';

export interface FileEntry {
  filename: string;
  contents: string;
}

export const ensureDirectoryExists = async (path: string): Promise<void> => {
  if (!existsSync(path)) {
    await mkdir(path, { recursive: true });
  }
};

export const writeFileToDataRoot = async (
  dataRoot: string,
  filename: string,
  content: string,
): Promise<string> => {
  await ensureDirectoryExists(dataRoot);
  const filePath = join(dataRoot, filename);
  await writeFile(filePath, content, 'utf-8');
  return filePath;
};

export const listFilesInDataRoot = async (dataRoot: string): Promise<FileEntry[]> => {
  if (!existsSync(dataRoot)) {
    return [];
  }

  const files = await readdir(dataRoot);

  const fileData = await Promise.all(
    files.map(async (filename) => {
      try {
        const filePath = join(dataRoot, filename);
        console.log(`Reading file: ${filePath}`);
        const contents = await readFile(filePath, 'utf-8');
        return { filename, contents };
      } catch (err) {
        console.error(err);
        return { filename: 'null', contents: 'null' };
      }
    }),
  );

  return fileData;
};
