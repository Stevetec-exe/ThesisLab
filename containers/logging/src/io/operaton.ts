import { now } from "../utils/time.ts";

const operatonUrl = process.env.OPERATON_URL ?? "http://localhost:8080/engine-rest";

export interface StartInstanceConfig {
    key: string,
    variables: {[key:string]:string}
}

export async function startInstance(config: StartInstanceConfig) {

    const variables = {} as {[key:string]:{type:string,value:string}}
    
    for(const [name,value] of Object.entries(config.variables)){
        variables[name] = {
            type:'string',
            value
        }
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