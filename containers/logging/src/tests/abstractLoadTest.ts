export abstract class AbstractLoadTest {
    constructor(config:AbstractLoadTestConfig){};
    async init(){};
    async run(){
        console.log("abstractRun")
    };
}

export interface AbstractLoadTestConfig {
    skip: boolean
}