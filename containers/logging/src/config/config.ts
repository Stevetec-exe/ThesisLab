import { readFileSync } from 'node:fs';
import JSONC from 'jsonc-simple-parser';
import type { SourceConfig } from '../@types/sourceConfig.js';
export const CONFIG = JSONC.parse(readFileSync('./config/config.jsonc', 'utf-8')) as SourceConfig;