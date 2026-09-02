import { Client, logger } from 'camunda-external-task-client-js';
import fs from 'fs/promises'

// configuration for the Client:
//  - 'baseUrl': url to the Process Engine
//  - 'logger': utility to automatically log important events
//  - 'asyncResponseTimeout': long polling timeout (then a new request will be issued)

const operatonUrl = process.env.OPERATON_URL ?? "http://localhost:8080/engine-rest";
const config = { baseUrl: operatonUrl, use: logger, asyncResponseTimeout: 10000 };

// create a Client instance with custom configuration
const client = new Client(config);

let count = 0;
let total = 0;
let last_instance = -1
let instances = [] as [number,number][]

// susbscribe to the topic: 'charge-card'
client.subscribe('service:poll', async function({ task, taskService }) {
  // Put your business logic here

  // Get a process variable
  const variables = task.variables.getAll()
  const spawnUnix = parseInt(variables['startTime'])
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
  
  //console.log(`Process ${task.id}/${task.businessKey}:`,variables)


  // Complete the task
  await taskService.complete(task);
});


setInterval(async()=>{
  const now = Date.now()
  
  if(now - last_instance > 1500 && last_instance != -1){
    console.log("Average process delay",total/count)
    await fs.writeFile(`data/${now}.txt`,instances.map(([start,end]) => `${start},${end},${end - start}`).join('\n'))
    last_instance = -1
    instances = []
  }
},500)