import express from 'express';
import fs from 'fs/promises'
import { download } from './s3.js';
const operatonUrl = process.env.OPERATON_URL ?? "http://localhost:8080/engine-rest";
const app = express()
app.use(express.json())
app.get('/',(req,res)=>{
  res.send("HTTP Push server root")
})


let count = 0;
let total = 0;
let last_instance = -1
let instances = [] as [number,number][]

app.use(express.json())

app.post('/syncronous',async(req,res)=>{
  const body = req.body??{}
  const spawnUnix = parseInt(String(body?.startTime || '-1'))

  const blob_id = body?.blob_id
  if(!blob_id){
    console.log("no blob_id provided. cannot pull from storage.")
  }else{
    const context_data = await download(blob_id)
    //console.log(context_data)
  }

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

  res.json({
    success: true,
    rng: Math.round(Math.random()*10000)
  })
})

app.post('/async',async(req,res)=>{
  const processID = req.body?.id
  if(!processID){
    console.error("cannot call async without ID!")
  }
  console.log("async job started from",processID)
  setTimeout(async()=>{
    console.log(`timeout fires for ${processID}`)
    const fres = await fetch(`${operatonUrl}/message`,{
      method:'POST',
      headers:{
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        messageName:"http-push-response",
        processInstanceId: processID,
        processVariables:{}
      })
    })
    const rtest = await fres.text()
    console.log("message result:",fres.status,rtest)
  },0)
  res.json({
    created: true
  })
})


setInterval(async()=>{
  const now = Date.now()
  
  if(now - last_instance > 1500 && last_instance != -1){
    console.log("Average process delay",total/count)
    await fs.writeFile(`data/${now}.txt`,instances.map(([start,end]) => `${start},${end},${end - start}`).join('\n'))
    last_instance = -1
    instances = []
  }
},500)

app.listen(1337)