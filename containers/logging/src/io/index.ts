import { startInstance as start_REST, type StartInstanceConfig as RESTConfig } from "./operaton.ts";
import { startInstance as start_AMQP, type StartInstanceConfig as AMQPConfig } from "./amqp.ts";

export async function startInstance(config:StartInstanceConfig) {
    await start_AMQP();
}
export type StartInstanceConfig = {
    
}