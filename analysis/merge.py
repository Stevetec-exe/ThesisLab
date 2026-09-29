import os
import json
import numpy as np

def compute_case_statistics(config,instace_stats):
    total_runtime = config.get('timing').get("end_test") - config.get('timing').get("start_test")
    instance_count = config.get('config').get("instanceCount")
    network_stats = config.get('net_total')
    
    instance_data = [[int(x) for x in i.split(',')] for i in instace_stats]
    instance_lifetimes = [
        i[1] - i[0] for i in instance_data
    ]
    
    return {
        "raw": {
            "time":{
                "total": total_runtime,
                "spawn": config.get('timing').get("end_spawn") - config.get('timing').get("start_test"),
                "drain": config.get('timing').get("end_test") - config.get('timing').get("end_spawn")
            },
            "network": network_stats
        },
        "network":{
            "average":{
                "tx": network_stats.get('tx') / instance_count,
                "rx": network_stats.get('rx') / instance_count
            }
        },
        "lifetimes":{
            "minimum": int(np.min(instance_lifetimes)),
            "average": sum(instance_lifetimes) / instance_count,
            "maximum": int(np.max(instance_lifetimes)),
            "p10": np.percentile(instance_lifetimes,10),
            "p25": np.percentile(instance_lifetimes,25),
            "p50": np.percentile(instance_lifetimes,50),
            "p75": np.percentile(instance_lifetimes,75),
            "p90": np.percentile(instance_lifetimes,90),
            "p95": np.percentile(instance_lifetimes,95),
            "p99": np.percentile(instance_lifetimes,99),
        }
    }


runs = os.listdir('data/raw')
latency_logs = os.listdir('data/scratch')

latency_logs = [
    int(l.split('.')[0]) for l in latency_logs
]

results = {
    
}

for run in runs:
    with open(f'data/raw/{run}') as f:
        log = json.load(f)
        
    architecture_tag = run.split('-')[2].split('.')[0]
    
    for case in log:
        end_test = case['timing']['end_test']
        log_unix = -1
        for logtime in latency_logs:
            if end_test - logtime < 2000 and end_test - logtime > -2000:
                log_unix = logtime
                break
        if(log_unix == -1):
            continue
        
        with open(f'data/scratch/{log_unix}.txt') as f:
            instance_statistics = f.readlines()
        
        stats = compute_case_statistics(case,instance_statistics)
        values = results.get(architecture_tag,{})
        
        group = values.get(case.get('config').get('label'),[])
        group.append(stats)
        values[case.get('config').get('label')] = group
        
        results[architecture_tag] = values


rid = log[0].get("timing").get("start_test")
with open(f'data/processed/results-{rid}.json','w') as f:
    json.dump(results,f,indent=2)