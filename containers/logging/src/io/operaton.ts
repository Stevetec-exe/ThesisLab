import { now } from "../utils/time.ts";

const operatonUrl = process.env.OPERATON_URL ?? "http://localhost:8080/engine-rest";

export interface StartInstanceConfig {
    key: string,
    payloadSize: number
}

const BLOCKSIZE = 500

export async function startInstance(config: StartInstanceConfig) {

    const variables = {} as {[key:string]:{type:string,value:string}}
    let payloadRemaining = config.payloadSize;
    let vid = 0
    while(payloadRemaining > 0){
        let vsize = Math.min(payloadRemaining,BLOCKSIZE)
        payloadRemaining -= vsize
        variables[`v${vid}`] = {
            type: 'String',
            value: 'A'.repeat(vsize)
        }
        vid++
    }
    variables['startTime'] = {
        type:'String',
        value: String(now())
    }
    const res = await fetch(`${operatonUrl}/process-definition/key/${config.key}/start`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            variables
        })
    })
    if (res.status < 200 || res.status > 299) {
        const err = await res.json()
        console.error(`[Start Instance] ${res.status}:`, err)
    }
}