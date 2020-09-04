# pm4py-distr
Support for distributed logs and computations in PM4Py.

See the currently supported API in api.txt

To execute locally an example (one master running on 5001 and two slaves running on 5002 and 5003)
just run "python main.py"

The example contains the partitioned version of the logs "receipt" and "roadtraffic".

## Experiment one for the thesis
Computation time of a Process Tree from a DFG:

0. Change the host address in main.py, main2.py and main3.py to the address where main.py will be run on.
Other addresses will be automatically idnetified by the engine.
1. Run python3 main.py, python3 main2.py and python3 main3.py each on one node
in that order.
2. Call the HTTP request http://137.226.117.71:5001/initialize?keyphrase=hello&process=receipt&doall=1&clean=1

You can select process receipt or roadtraffic

## Experiment two for the thesis

0. Change the host address in main.py, main2.py and main3.py to the address where main.py will be run on.
Other addresses will be automatically idnetified by the engine.
1. Run python3 main.py, python3 main2.py and python3 main3.py each on one node
in that order.

2. Call the HTTP request http://137.226.117.71:5001/initialize?keyphrase=hello&process=test1&doall=1&clean=1

3. If we want to set the resource value multipliers call http://137.226.117.71:5001/setResMultiplier?keyphrase=hello&cpu=1&ram=1&disk=1&k=100

4. If we have need an artificial DFG call http://137.226.117.71:5001/createDFG?keyphrase=hello&dfgname=test1

5. Call the HTTP request http://137.226.117.71:5001/distributedIMD?keyphrase=hello&process=test1&created=1

6. Results can be seen on http://137.226.117.71:5001/resultIMD?keyphrase=hello&process=test1











## Easy setup after running python main.py

1. Run everything needed for Inductive Miner directly-follows based with following call.
It all steps until DFG calculation if doall=0, if doall=1 it will compute a DFG based on the log. For cleaning old calculations use clean=1.

    http://localhost:5001/initialize?keyphrase=hello&process=receipt&doall=1&clean=1

2. To get the resource allocation function use:
    
    http://localhost:5001/resAllFct?keyphrase=hello&cpu=1&ram=1&disk=0&k=10
    
    Each value for CPU, RAM and DISK will give a weight on each resource. 
    k is the slope variable for the RAM function, default is set to 10.
    
3. To run the a distributed IM DFG:
    
    http://localhost:5001/distributedIMD?keyphrase=hello&process=receipt
    
4. To see the result as a tree: (it might take a while)

    http://localhost:5001/resultIMD?keyphrase=hello&process=receipt


    
## Example of usage of the distributed services (default keyphrase is "hello"):

1) ALLOCATION OF THE PARTITIONS BETWEEN THE SLAVES

    http://localhost:5001/doLogAssignment?keyphrase=hello

2) CALCULATION OF THE DFG

    http://localhost:5001/calculateDfg?keyphrase=hello&process=receipt

3) USE INDUCTIVE MINER-DIRECT FOLLOWS BASED

    i) http://localhost:5001/distributedIMD?keyphrase=hello&process=receipt

    ii) For comparison without distributing the work

    http://localhost:5001/simpleIMD?keyphrase=hello&process=receipt

## Configuration of the keyphrase

The keyphrase that is shared between the slaves and the master is contained in the pm4pydistr.configuration file.

## Custom executions of master/slave

If instead of running the default example, you want to execute the master/slaves in custom configuration,
follow the process:

1) REMOVE THE EXAMPLE FILES

Remove the "master.db" database and the "master" folder

2) CREATE A "master" FOLDER CONTAINING THE PARTITIONED DATASETS THAT YOU WANT TO USE

See the PARTITIONING.txt file for instructions on how to partition a log file into a partitioned dataset!


3) LAUNCH THE MASTER

Launch the master with the command: python launch.py --type master --conf master --port 5001
(replace possibly the port, it is by default listening on 0.0.0.0)

4) LAUNCH THE SLAVES

Launch a slave (that are master-aware) with the command:

python launch.py --type slave --conf slave1 --port 5002 --master-host 127.0.0.1 --master-port 5001
(replace possibly the port used by the slave, and the host/port that points to the master).


