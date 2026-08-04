import Pyro5.api
import os
import json
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from datetime import datetime
import pandas as pd
import socket

RANDOM_STATE = 42
POLL_INTERVAL = 0.5
N_ESTIMATORS = 100
N_JOBS = 1  # keep at 1-2 when running multiple worker processes on the same machine,
            # otherwise each RandomForest fights the others for all CPU cores.

@Pyro5.api.expose
class Worker:
    def __init__(self, node_name):
        self.node_name = node_name

    """
        Method for training (from start_instance row, to last_instance row).
        Returns a generated Random Forest for the batch

        ref: https://www.youtube.com/watch?v=_QuGM_FW9eo
    """
    def ImaxTrain(self, X_train, X_test, y_train, y_test, subset):
        #convert back to df and series
        X_train = pd.DataFrame.from_dict(X_train)
        X_test = pd.DataFrame.from_dict(X_test)
        y_train = pd.Series(y_train)
        y_test = pd.Series(y_test)

        results = {}
        last_instance = int(len(X_train) * subset)

        # subset is from the first row until % of total
        X_subset = X_train.iloc[:last_instance]
        y_subset = y_train.iloc[:last_instance]
        rf = RandomForestClassifier(
                n_estimators=N_ESTIMATORS,
                random_state=RANDOM_STATE,
                n_jobs=N_JOBS
            )

        start = datetime.now()
        rf.fit(X_subset, y_subset)
        y_pred = rf.predict(X_test)
        end = datetime.now()

        # training results
        results['duration'] = (end - start).total_seconds()
        results['score'] = rf.score(X_test, y_test)
        results['report'] = classification_report(y_test, y_pred, output_dict=True)
        print(f"Worker {self.node_name} finished subset={int(subset*100)}%\n")
        return results


def main():
    hostname = socket.gethostname()
    node_name = os.getenv("NODE_NAME", default=None)

    # create a pyro daemon for dispatching rpc
    # use hostname assigned to container
    daemon = Pyro5.api.Daemon(host=hostname)

    # instantiate worker object
    worker = Worker(node_name)

    # register the worker object and generate uri
    uri = daemon.register(worker)

    if node_name == None:
        print(f"Failed to fetch Worker 'NODE_NAME' environment variable.")
        return

    # register worker to name server
    name_server = Pyro5.api.locate_ns(host="nameserver")
    friendly_name = f"workers.{node_name}"
    name_server.register(friendly_name, uri)
    print(f"Worker {node_name} registered to Name Server as '{friendly_name}'")
        
    daemon.requestLoop()

if __name__ == "__main__":
    main()