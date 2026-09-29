import { assert } from "node:console";
import { AbstractLoadTest, type AbstractLoadTestConfig } from "./abstractLoadTest.ts"
import { delayMs } from "../utils/time.ts";
import { startInstance, startMockedInstance, type StartInstanceConfig, type StartMockedInstanceConfig } from "../io/index.ts";

export interface ConstantLoadTestConfig extends AbstractLoadTestConfig{
    instanceCount: number
    delayMs: number
    instanceConfig: StartMockedInstanceConfig,
}

export class ConstantLoadTest extends AbstractLoadTest {

    private config: ConstantLoadTestConfig;
    constructor(config: ConstantLoadTestConfig){
        super(config);
        this.config = config
    }

    async run(){
        for(let i = 0;i < this.config.instanceCount;i++){
            await startMockedInstance(this.config.instanceConfig)
            await delayMs(this.config.delayMs);
        }
    }
}