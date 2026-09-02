import { startInstance as start_REST, type StartInstanceConfig as RESTConfig } from "./operaton.ts";
import { startInstance as start_AMQP, type StartInstanceConfig as AMQPConfig } from "./amqp.ts";
import { now } from "../utils/time.ts";

export async function startInstance(config:StartInstanceConfig) {
    await start_AMQP({
        ref: 'StartInstance',
        variables:{
            message:JSON.stringify({
                startTime: String(now())
            }),
        }
    });
}
export type StartInstanceConfig = {
    key: string,
    payloadSize: number  
}