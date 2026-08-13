#!/usr/bin/env node

import amqp from 'amqplib';

const URI = process.env.AMQP_HOST ?? "amqp://user:password@localhost:5672/%2F"
const QUEUE_NAME = "amqp-connector-services"

async function main() {
    const connection = await amqp.connect(URI);
    const channel = await connection.createChannel();

    await channel.assertQueue(QUEUE_NAME, {
        durable: true,
        arguments: { 'x-queue-type': 'quorum' }
    });

    console.log(" [*] Waiting for messages in %s. To exit press CTRL+C", QUEUE_NAME);

    channel.consume(QUEUE_NAME, function(msg) {
        console.log(" [x] Received %s", msg.content.toString());
    }, {
        noAck: true
    });
}

main();