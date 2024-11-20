import argparse
from robotics_api.settings import *


def launch_robot_job(job_type="", run_cmd="singleshot"):
    if "continuous" in run_cmd:
        run_cmd = "rapidfire --nlaunches infinite --sleep 10"

    if "robot" in job_type:
        print(f"Launching robot jobs {run_cmd}...")
        subprocess.call('rlaunch -w {} {}'.format(ROBOT_FWORKER, run_cmd))
    if "instr" in job_type:
        print(f"Launching instrument jobs {run_cmd}...")
        subprocess.call('rlaunch -w {} {}'.format(INSTRUMENT_FWORKER, run_cmd))
    if "proc" in job_type:
        print(f"Launching process jobs {run_cmd}...")
        subprocess.call('rlaunch -w {} {}'.format(PROCESS_FWORKER, run_cmd))
    else:
        print(f"Launching jobs {run_cmd}...")
        subprocess.call('rlaunch {}'.format(run_cmd))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Launch firworks jobs")
    parser.add_argument("run_cmd", help="Fireworks run command.", default="singleshot")
    parser.add_argument("-t", "--job_type", help="Job type to launch", default="")
    args = parser.parse_args()

    launch_robot_job(args.job_type, args.run_cmd)
