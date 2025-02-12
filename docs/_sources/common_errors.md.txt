# Common Errors

* `NameError: Argument wflow_name does not match instance current_wflow_name`: You are trying to run a
workflow that is not initiated. You are likely trying to run two workflows at once. Ensure all other
workflows are COMPLETED, PAUSED, or DEFUSED, then rerun the `init_` firework from the workflow you
are trying to run.
* `ValueError: Conductivity calibration for today does not exist.`: You are trying to measure conductivity
(processing CA experiment files so trying to get the cell constant) when you have not run a CA
calibration that day. Run a CA calibration every day you perform CA experiments.
* `waiting for balance_01 balance results for 1.0 seconds...`: The software is trying to read/tare the balance, 
but the balance is likely not on. Check that the balance is on. 
* `Exception: ('Error: Robot did not reach the desired joint angles: '`: The robot just decides to be difficult 
sometimes and not do what is told...I'm not sure why. Rerun the FIZZLED firework and launch again. This also can occur
after operating the robot with the Kinova web interface (http://192.168.1.10/). 
* `FileNotFoundError: The datafile __________ was not found.`: A potentiostat measurement was not successfully completed.
After a measurement is run, the API checks for the existence of the expected output datafile. This error means that
datafile was not found. Check that the potentiostat are on. Check that the CHI GUIs are closed out. 
* `Self defusing Firetask ____`: The API intentionally fizzled a FireTask. THIS IS NOT A BIG DEAL--DON'T WORRY ABOUT IT!
This usually happens if the station a FireTask needs is already in use. Every time a `finish_` FireTask is completed, 
the API will automatically rerun this FireTask. In principle, the station will eventually become available.  
* In general, **read error messages**! Error messages should explain what went wrong. You can
also use the traceback to find where in the code the error occurred.


*!! This page is in still in development*
