import express from 'express';
const operatonUrl = process.env.OPERATON_URL ?? "http://localhost:8080/engine-rest";
const app = express()
app.use(express.json())
app.get('/',(req,res)=>{
  res.send("HTTP Push server root")
})

app.get('/syncronous',(req,res)=>{
  console.log("sync job started")
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
        processVariables:{
          "async-rng":{
            value: Math.round(Math.random()*10000),
            type: "integer"
          }
        }
      })
    })
    const rtest = await fres.text()
    console.log("message result:",fres.status,rtest)
  },2000)
  res.json({
    created: true
  })
})

app.listen(1337)