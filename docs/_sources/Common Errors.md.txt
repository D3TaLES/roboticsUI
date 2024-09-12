# Common Errors

* `NameError: Argument wflow_name does not match instance current_wflow_name`: You are trying to run a 
workflow that is not initiated. You are likely trying to run two workflows at once. Ensure all other 
workflows are COMPLETED, PAUSED, or DEFUSED, then rerun the `init_` firework from the workflow you 
are trying to run. 
* `ValueError: Conductivity calibration for today does not exist.`: You are trying to measure conductivity
(processing CA experiment files so trying to get the cell constant) when you have not run a CA 
calibration that day. Run a CA calibration every day you perform CA experiments. 
* 
* In general, **read error messages**! Error messages should explain what went wrong. You can
also use the traceback to find where in the code the error occurred. 
