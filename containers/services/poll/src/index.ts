import { Client, logger } from 'camunda-external-task-client-js';

// configuration for the Client:
//  - 'baseUrl': url to the Process Engine
//  - 'logger': utility to automatically log important events
//  - 'asyncResponseTimeout': long polling timeout (then a new request will be issued)

const operatonUrl = process.env.OPERATON_URL ?? "http://localhost:8080/engine-rest";
const config = { baseUrl: operatonUrl, use: logger, asyncResponseTimeout: 10000 };

// create a Client instance with custom configuration
const client = new Client(config);

// susbscribe to the topic: 'charge-card'
client.subscribe('service:poll', async function({ task, taskService }) {
  // Put your business logic here

  // Get a process variable
  const variables = task.variables.getAll()
  console.log(`Process ${task.id}/${task.businessKey}:`,variables)


  // Complete the task
  await taskService.complete(task);
});
