import fs from "node:fs/promises"

type LogItem = {
    [key:string]:any
}


export class Logger{
    private streamName: string
    private logBuffer = [] as LogItem[]
    constructor(streamName?: string){
        if(!streamName){
            this.streamName = `raw-${Math.floor(+new Date() / 1000)}`
        }else{
            this.streamName = streamName
        }
    }

    logSync(data:LogItem) {
        this.logBuffer.push(data)
    }

    async save(tag?:string){
        await fs.writeFile(`data/raw/${this.streamName}${tag?'-'+tag:''}.json`,JSON.stringify(this.logBuffer,null,4))
    }
}