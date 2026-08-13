import { CONFIG } from "../config/config.ts"
import fs from 'node:fs';
import path from 'node:path';

export function loadAll() {
    const datafiles = fs.readdirSync(CONFIG.input.sourceDir)

    console.log(datafiles)

    const RAW = []
    for (const filename of datafiles) {
        const data = JSON.parse(fs.readFileSync(path.join(CONFIG.input.sourceDir, filename)).toString())
        RAW.push(data)
    }
    return RAW
}