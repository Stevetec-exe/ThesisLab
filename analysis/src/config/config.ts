export type GlobalConfig = {
    input:{
        sourceDir: string
    },
    output:{
        outFile: string
    }
}
import fs from 'node:fs';
import JSONC from 'jsonc-simple-parser'; 
export const CONFIG = JSONC.parse(fs.readFileSync('../config/postprocess.jsonc', 'utf-8')) as GlobalConfig;

export const TESTCASES = JSONC.parse(fs.readFileSync('../config/testcases.jsonc', 'utf-8'));