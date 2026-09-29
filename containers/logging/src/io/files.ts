import fs from "node:fs/promises";

export async function waitForNewLogfile(dir: string): Promise<string> {
  const initialFiles = new Set(await fs.readdir(dir));

  for await (const _event of fs.watch(dir)) {
    const currentFiles = await fs.readdir(dir);

    const newFile = currentFiles.find(
      (filename) => !initialFiles.has(filename),
    );

    if (newFile) {
      return newFile;
    }
  }

  throw new Error("File watcher stopped unexpectedly");
}