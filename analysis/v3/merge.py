import json
import os

def get_folder_files(path:str):
    return list(os.walk(path))[0][2]

def merge_group(tag,file_names,basepath='data/processed/correlated/'):
    ...
    print(tag,'->',file_names)
    
    for file_name in file_names:
        with open(basepath+file_name) as f:
            stream = json.load(f)

if __name__ == '__main__':
    correlated_logs = get_folder_files('data/processed/correlated')
    
    # Group by log stream tag
    tagged_groups = {}
    for i,logname in enumerate(correlated_logs):
        log_tag = logname.split('.')[0].split('-')[-1]
        
        group = tagged_groups.get(log_tag,[])
        group.append(logname)
        tagged_groups[log_tag] = group
    
    for group_name,stream_names in tagged_groups.items():
        merge_group(group_name,stream_names)