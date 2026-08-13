import { assert } from "node:console";
import { AbstractLoadTest, type AbstractLoadTestConfig } from "./abstractLoadTest.ts"
import { delayMs } from "../utils/time.ts";
import { startInstance, type StartInstanceConfig } from "../io/index.ts";

export interface ConstantLoadTestConfig extends AbstractLoadTestConfig{
    instanceCount: number
    delayMs: number
    instanceConfig: StartInstanceConfig
}

export class ConstantLoadTest extends AbstractLoadTest {

    private config: ConstantLoadTestConfig;
    constructor(config: ConstantLoadTestConfig){
        super(config);
        this.config = config
    }

    async run(){
        for(let i = 0;i < this.config.instanceCount;i++){
            await startInstance(this.config.instanceConfig)
            await delayMs(this.config.delayMs);
        }
    }
}