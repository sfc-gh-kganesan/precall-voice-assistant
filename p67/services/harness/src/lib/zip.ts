import { mkdir, rm } from 'fs/promises';
import { join } from 'path';
import { tmpdir } from 'os';
import { randomUUID } from 'crypto';
import AdmZip from 'adm-zip';

interface UnzipResult {
  tempDir: string;
  files: string[];
}

export async function unzipToTemp(zipPath: string): Promise<UnzipResult> {
  const tempDir = join(tmpdir(), `unzip-${randomUUID()}`);
  await mkdir(tempDir, { recursive: true });

  try {
    const zip = new AdmZip(zipPath);
    zip.extractAllTo(tempDir, true);

    const zipEntries = zip.getEntries();
    const files = zipEntries.map((entry) => entry.entryName);

    return { tempDir, files };
  } catch (error) {
    await rm(tempDir, { recursive: true, force: true });
    throw error;
  }
}
