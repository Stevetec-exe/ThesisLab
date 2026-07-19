import { assert } from "node:console";
import { AbstractLoadTest, type AbstractLoadTestConfig } from "./abstractLoadTest.ts"
import { delayMs } from "../utils/time.ts";
import { startInstance, type StartInstanceConfig } from "../io/operaton.ts";

export interface IdleLoadTestConfig extends AbstractLoadTestConfig{
    delayMs: number
}

export class IdleLoadTest extends AbstractLoadTest {

    private config: IdleLoadTestConfig;
    constructor(config: IdleLoadTestConfig){
        super(config);
        this.config = config
        assert(this.config.delayMs >= 0)
    }

    async run(){
        await delayMs(this.config.delayMs);
    }
}