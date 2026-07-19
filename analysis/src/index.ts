import { readFileSync } from 'node:fs';
import JSONC from 'jsonc-simple-parser'; 
type GlobalConfig = {

}

const CONFIG = JSONC.parse(readFileSync('../config/postprocess.jsonc', 'utf-8')) as GlobalConfig;

console.log(CONFIG)