import json
import os
import numpy as np

import numpy as np

def statistics_from_stream(data):
    return {
    "count": int(len(data)),
    "min": int(np.min(data)),
    "max": int(np.max(data)),
    "mean": float(np.mean(data)),
    "std_dev": float(np.std(data)),
    "p50": float(np.percentile(data, 50)),
    "p90": float(np.percentile(data, 90)),
    "p95": float(np.percentile(data, 95)),
    "p99": float(np.percentile(data, 99)),
}

def get_folder_files(path:str):
    return list(os.walk(path))[0][2]

def get_instance_log_name(target_time:int,basepath='data/scratch',margin=5000):
    scratchlog_filenames = get_folder_files(basepath)
    logtimes = [int(x.split('.')[0]) for x in scratchlog_filenames]
    for logtime in logtimes:
        delta = abs(logtime - target_time)
        if delta < margin:
            break
    else:
        return None
    
    logfile_name = f'{basepath}/{logtime}.txt'
    return logfile_name

def correlate_from_raw_log(path:str):
    with open(path) as f:
        raw_log = json.load(f)
    
    for testcase in raw_log:
        #print(testcase)
        testcase_end = testcase.get('timing').get('end_test')
        caselog = get_instance_log_name(testcase_end)
        
        with open(caselog) as cl:
            instance_stats_raw = cl.readlines()
        
        instance_stats_split = [
            instance.strip().split(',') for instance in instance_stats_raw
        ]
        
        instance_stats = [
            {
                'start':int(instance[0]),
                'end':int(instance[1]),
                'duration':int(instance[2]),
             } for instance in instance_stats_split
        ]
        
        # enhance process from instance data.
        # only write statistics not raw log, VSCode sometimes
        # really doesn't like 3mb json files
        
        start_times = np.asarray(list(i['start'] for i in instance_stats))
        start_times.sort()  # poll does out-of-order processing sometimes and it breaks the deltas
        
        end_times = np.asarray(list(i['end'] for i in instance_stats))
        end_times.sort()  # poll does out-of-order processing sometimes and it breaks the deltas
        
        durations = np.asarray(list(i['duration'] for i in instance_stats))
        
        # The end-time in the log is after logfile detection not end of instance
        # We can simply replace it with more accurate data while available.
        # This error may be as high as 1.5 seconds.
        testcase['timing']['end_test'] = int(end_times[-1])
        
        # If this were ideal zero jitter zero overhead
        # we'd get deltas consistently equal to timing.delayMs
        start_deltas = np.diff(start_times)
        end_deltas = np.diff(end_times)
        
        testcase['instance_statistics'] = {
            'lifetime':statistics_from_stream(durations),
            'start_deltas':statistics_from_stream(start_deltas),
            'end_deltas':statistics_from_stream(end_deltas),
            'spawns':{
                'avg_spawns_per_second': 1000 / start_deltas.mean(),
                'avg_completes_per_second': 1000 / end_deltas.mean()
            }
        }
        #testcase['instances'] = instance_stats
    
    return raw_log

if __name__ == '__main__':
    runlogs = get_folder_files('data/raw')
    for i,logname in enumerate(runlogs):
        print(f'{i+1}/{len(runlogs)}',logname)
        hydrated_log = correlate_from_raw_log(f'data/raw/{logname}')
        with open(f'data/processed/correlated/{logname}','w') as outfile:
            json.dump(hydrated_log,outfile,indent=4)