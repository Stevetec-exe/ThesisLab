import amqp from 'amqplib';
export interface StartInstanceConfig {
    ref: string,
    variables?: { [key: string]: string }
}

export async function startInstance() {
    await publish(QUEUE_NAME,JSON.stringify({
        ref:"StartInstance",
        variables:{
            message:"Hello from Node.js"
        }
    }))
}

let connection: amqp.ChannelModel;
let channel: amqp.Channel;
const QUEUE_NAME = "amqp-connector-engine"
const URI = process.env.AMQP_HOST ?? "amqp://user:password@localhost:5672/%2F"
export async function init() {
    console.log(URI)
    connection = await amqp.connect(URI);
    channel = await connection.createChannel();

    await channel.assertQueue(QUEUE_NAME, {
        durable: true,
        arguments: { 'x-queue-type': 'quorum' },
        
    });
    return true
}

export async function publish(queue: string,msg: string) {
    channel.sendToQueue(queue, Buffer.from(msg));
}

export async function close() {
    await channel.close();
    await connection.close();
}