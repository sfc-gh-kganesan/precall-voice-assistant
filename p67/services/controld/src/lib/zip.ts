import AdmZip from 'adm-zip';

interface UnzipResult {
    dir: string;
    files: string[];
}

export async function unzip(
    zippedData: string | Buffer,
    targetDir: string,
): Promise<UnzipResult> {
    const zip = new AdmZip(zippedData);
    zip.extractAllTo(targetDir, true);
    const zipEntries = zip.getEntries();
    const files = zipEntries.map((entry) => entry.entryName);
    return { dir: targetDir, files };
}
