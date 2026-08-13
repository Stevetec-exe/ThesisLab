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

    async save(){
        await fs.writeFile(`data/${this.streamName}.json`,JSON.stringify(this.logBuffer,null,4))
    }
}