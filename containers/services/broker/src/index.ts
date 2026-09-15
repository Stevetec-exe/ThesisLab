#!/usr/bin/env node
import fs from 'fs/promises'
import amqp from 'amqplib';

const URI = process.env.AMQP_HOST ?? "amqp://user:password@localhost:5672/%2F"
const QUEUE_NAME = "amqp-connector-services"

let count = 0;
let total = 0;
let last_instance = -1
let instances = [] as [number,number][]

async function main() {
    const connection = await amqp.connect(URI);
    const channel = await connection.createChannel();
    console.log("asserting queue")
    await channel.assertQueue(QUEUE_NAME, {
        durable: true,
        arguments: { 'x-queue-type': 'quorum' }
    });

    console.log(" [*] Waiting for messages in %s. To exit press CTRL+C", QUEUE_NAME);

    channel.consume(QUEUE_NAME, function(msg) {
        if(!msg){
            console.log("[Broker service] empty message")
            return
        }
        let payload = {} as any
        try{
            payload = JSON.parse(msg.content.toString())
        }catch(e){
            console.error("could not decode payload: Invalid JSON")
            console.error(msg)
            console.error(e)
            return
        }
        //console.log(" [x] Received %s", msg.content.toString());

        const spawnUnix = parseInt(String(payload?.startTime?.toString() || '-1'))
        const now = Date.now()
        const diff = now - spawnUnix
        if(last_instance == -1){
            total = 0
            count = 0
        }
        total += diff
        count += 1
        instances.push([spawnUnix,now])
        last_instance = now

    }, {
        noAck: true
    });
}

setInterval(async()=>{
  const now = Date.now()
  
  if(now - last_instance > 1500 && last_instance != -1){
    console.log("Average process delay",total/count)
    await fs.writeFile(`data/${now}.txt`,instances.map(([start,end]) => `${start},${end},${end - start}`).join('\n'))
    last_instance = -1
    instances = []
  }
},500)


;(async ()=>{
    await new Promise(resolve => setTimeout(resolve, 7500))
while(true){
    try{
        console.log("Starting broker service")
        await main();
        await new Promise(resolve => setTimeout(resolve, 2500))
        break
    }catch(e){
        console.log(e)
    }
}
})()