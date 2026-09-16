import { startInstance as start_REST, type StartInstanceConfig as RESTConfig } from "./operaton.ts";
import { startInstance as start_AMQP, type StartInstanceConfig as AMQPConfig } from "./amqp.ts";
import { now } from "../utils/time.ts";
import { upload as upload_to_s3 } from "./s3.ts";

const BLOCKSIZE = 1000

type SendType = 'engine-rest' | 'amqp'

export async function startInstance(config: StartInstanceConfig, target: SendType = 'engine-rest') {
    if (target == 'amqp') {
        await start_AMQP({
            messageName: `event:start:${config.processName}`,

            processVariables: {
                ...config.variables,
                startTime: String(now())
            }
        });
    }else if(target == 'engine-rest'){
        await start_REST({
            key: config.processName,
            variables:{
                ...config.variables,
                startTime: String(now()),
            }
        })
    }
}

export function get_dummy_payload_variables(size:number,blockSize:number = BLOCKSIZE){
    const dataVars = {} as { [key: string]: string }
    let remainingPayload = size;
    let i = 0;
    while (remainingPayload > 0) {
        const blocksize = Math.min(remainingPayload, blockSize)
        remainingPayload -= blocksize
        dataVars[`v${i++}`] = 'A'.repeat(blocksize)
    }
    return dataVars
}

let _ARCHITECTURE = 'push' as 'push'|'poll'|'amqp'|'s3'

export function getCurrentArchitectureChannel(){
    return _ARCHITECTURE;
}

export function setCurrentArchitectureChannel(c: typeof _ARCHITECTURE){
    _ARCHITECTURE = c;
}

/** Encodes infrastructure knowlege. Given a measurement target will fire the process instance with dummy data pushed over the correct channel. */
export async function startMockedInstance(config:StartMockedInstanceConfig,channel: typeof _ARCHITECTURE | ':global' = ':global'){
    if(channel == ':global'){
        channel = getCurrentArchitectureChannel()
    }

    if(channel == 'push'){
        startInstance({
            processName: 'proc-min-push',
            variables: get_dummy_payload_variables(config.payloadSize)
        },'engine-rest')
    }else if(channel == 'poll'){
        startInstance({
            processName: 'proc-min-poll',
            variables: get_dummy_payload_variables(config.payloadSize)
        },'engine-rest')
    }else if(channel == 'amqp'){
        startInstance({
            processName: 'proc-min-amqp',
            variables: get_dummy_payload_variables(config.payloadSize)
        },'amqp')
    }else if(channel == 's3'){
        const blob_id = await upload_to_s3(Buffer.alloc(config.payloadSize, 0x41))
        startInstance({
            processName: 'proc-min-storage',
            variables: {
                blob_id
            }
        },'engine-rest')
    }
}

export type StartInstanceConfig = {
    processName: string,
    variables: { [key: string]: string }
}

export type StartMockedInstanceConfig = {
    payloadSize: number,
}