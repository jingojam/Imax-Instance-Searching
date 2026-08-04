# Imax-Instance-Searching
## For Docker containerized topology
### To build the application:
- `sudo docker compose build --no-cache`
### To run the application:
- `sudo docker compose up` (use `-d` flag at the end to detach from the output)
### To stop the application:
- `sudo docker compose down` (use `-v` flag at the end to completely wipe the environment)
## For non-containerized topology
Make sure to run all of these on dedicated machines/nodes under the same physical/virtual network. (Note: It is important to run the nameserver first, followed by the worker, then lastly the master).
Additionally, the application depends on these modules:
- `pip3 install Pyro5`
- `pip3 install -U scikit-learn`
- `pip3 install pandas`
- `pip3 install kneed`
- `pip3 install kneed[plot]`
- `pip3 install notebook`
- `python3 -m pip install -U matplotlib`
### Start the nameserver:
- `python3 -m Pyro5.nameserver -n 0.0.0.0`
### Then the worker node
- `python3 worker.py`
### Then start the master node:
- `python3 master.py`
## Others
### On Linux
`pip3 install ...` requires `.venv`. Open the terminal and do:
- `cd` to this project directory
- `source .venv/bin/activate`
