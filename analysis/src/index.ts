import { loadAll } from "./preprocess/index.ts";
import { mkConfig, generateCsv, asString } from "export-to-csv";
import { writeFile } from "node:fs";
import { Buffer } from "node:buffer";
import { CONFIG, TESTCASES } from "./config/config.ts";

const RAW = loadAll()

console.log(RAW)

const csvData = RAW.map((run,i)=>{
    const line = {id: i} as {[key:string]:any}
    for(const test of run){
        const config = TESTCASES.tests[test.testId]
        const label = config.label || `${config.type}-${test.testId}`

        line[`${label}_tx`] = test.net_total.tx
        line[`${label}_rx`] = test.net_total.rx
    }
    return line
})

const csvConfig = mkConfig({ useKeysAsHeaders: true, filename: CONFIG.output.outFile });

const csv = generateCsv(csvConfig)(csvData);
const filename = `${csvConfig.filename}.csv`;
const csvBuffer = new Uint8Array(Buffer.from(asString(csv)));

// Write the csv file to disk
writeFile(filename, csvBuffer, (err) => {
  if (err) throw err;
  console.log("file saved: ", filename);
});