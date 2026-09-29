export abstract class AbstractLoadTest {
    constructor(config:AbstractLoadTestConfig){};
    async init(){};
    async run(){
        console.log("abstractRun")
    };
}

import type { SourceConfig } from '../@types/sourceConfig.js';
export interface AbstractLoadTestConfig {
    skip: boolean,
    timing: Partial<SourceConfig['timing']>
}