import wandb
import subprocess
import os
import json
import time
import myconfig
from datetime import datetime


# check echo from 'sacct' to tell the job status
def check_status(status):
    rtn = 'RUNNING'
    
    lines = status.split('\n')
    for line in lines:
        line = line.strip()
        if line == '':
            continue
        if 'FAILED' in line:
            rtn = 'FAILED'
            break
        elif 'COMPLETED' not in line:
            rtn = 'PENDING'
            break
    else:
        rtn = 'COMPLETED'
        
    return rtn


def wrap_task(config=None):
    # recieve config for this run from Sweep Controller

    with wandb.init(config=config):
        agent_id = wandb.run.id
        agent_dir = wandb.run.dir
        config = dict(wandb.config)

        # §§ DB folder
        config['origin_path'] = '/Dataset_res250/'

        config['debug'] = False
        config['bp'] = False
        
        config['batch'] = 64
        config['accumulation_steps'] = config['full_batch'] // config['batch']
        config['epoch'] = 10000
        config['test_batch'] = 50
        config['nn_lr'] = config['lr']
        config['es_mindelta'] = 0.5
        config['es_endure'] = 30

        config['num_features_in'] = 10

        config['num_features_out'] = 1
        config['emb_hidden_dim'] = config['emb_dim'] * 4
        
        config['seed'] = 1
        config['model'] = 'PEGNN'

        config['fold'] = 0
        config['holdout'] = [0, 1]
        config['lowest_rank'] = 1
        
        # wait until available pipe slot

        # §§ slurm command: squeue
        while True:
            cmd = f"squeue -n {myconfig.project_name}"
            status = subprocess.check_output(cmd, shell=True).decode()
            lines = status.split('\n')[1:-1]
            if len(lines) <= myconfig.pool_size:
                break
            else:
                time.sleep(60)

        # partition gpu_4 => dev_gpu_4
        # time = 24:00:00 => 00:30:00
        # then build up the slurm script

        job_script = \
f"""#!/bin/bash
#SBATCH --job-name={myconfig.project_name}
#SBATCH --partition=gpu_4
#SBATCH --gres=gpu:4
#SBATCH --error={myconfig.log_path}%x.%j.err
#SBATCH --output={myconfig.log_path}%x.%j.out
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user={myconfig.e_mail}
#SBATCH --export=ALL
#SBATCH --time=24:00:00

eval \"$(conda shell.bash hook)\"
conda activate {myconfig.conda_env}
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:{myconfig.conda_env}/lib

job_id=$SLURM_JOB_ID
python {myconfig.train_script_name} $job_id '{json.dumps(config)}' {agent_id} {agent_dir}
"""


        # wandb config agent id agent dir
        
        # Write job submission script to a file
        # change to windows cmd
        with open(myconfig.slurm_scripts_path + f"{wandb.run.id}.sbatch", "w") as f:
            f.write(job_script)

        # current_direcorty =os.getcwd()
        # slurm_scripts_diretocry = os.path.join(current_direcorty, myconfig.slurm_scripts_path)
        # with open( slurm_scripts_diretocry + f"{wandb.run.id}.cmd", "w") as f:
        #     f.write(job_script)
        
        # Submit job to Slurm system and get job ID

        # change script to windows cmd
        cmd = "sbatch " + myconfig.slurm_scripts_path + f"{wandb.run.id}.sbatch"
        # cmd = slurm_scripts_diretocry + f"{wandb.run.id}.cmd"

        # change to windows cmd
        output = subprocess.check_output(cmd, shell=True).decode().strip()
        # subprocess.run([cmd] , shell=True)

        # close for now
        job_id = output.split()[-1]


        wandb.log({
            "job_id" : job_id,
        })
        return job_id
        
           
if __name__ == '__main__':
    rtn = wrap_task()
    print(f'******************************************************* Process Finished with code {rtn}')
    wandb.finish()
