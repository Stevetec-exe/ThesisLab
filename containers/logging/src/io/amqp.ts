import amqp from 'amqplib';
import { now } from '../utils/time.ts';
export interface StartInstanceConfig {
    ref: string,
    variables?: { [key: string]: string }
}

export async function startInstance(config:StartInstanceConfig) {
    await publish(QUEUE_NAME,JSON.stringify({
        ref:config.ref,
        variables:config.variables
    }))
}

let connection: amqp.ChannelModel;
let channel: amqp.Channel;
const QUEUE_NAME = "amqp-connector-engine"
const URI = process.env.AMQP_HOST ?? "amqp://user:password@localhost:5672/%2F"
export async function init() {
    console.log(URI)
    try{
        connection = await amqp.connect(URI);
        channel = await connection.createChannel();
    
        await channel.assertQueue(QUEUE_NAME, {
            durable: true,
            arguments: { 'x-queue-type': 'quorum' },
            
        });
        return true
    }catch(e){
        console.error("[AMQP] Could not connect:",e)
        return false
    }
}

export async function publish(queue: string,msg: string) {
    channel.sendToQueue(queue, Buffer.from(msg));
}

export async function close() {
    await channel.close();
    await connection.close();
}