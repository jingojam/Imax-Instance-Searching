import Pyro5.api
import asyncio
import os
import json
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from datetime import datetime
import pandas as pd
import socket

@Pyro5.api.expose
class Worker:
    def __init(self):
        pass

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
        rf = RandomForestClassifier(random_state=42)
        start = datetime.now()
        rf.fit(X_subset, y_subset)
        y_pred = rf.predict(X_test)
        end = datetime.now()

        # training results
        results['score'] = rf.score(X_test, y_test)
        results['report'] = classification_report(y_test, y_pred)
        results['duration'] = end - start
        print(f"Finished subset {subset}\n")
        return results


def main():
    # create a pyro daemon for dispatching rpc
    # use hostname assigned to container
    daemon = Pyro5.api.Daemon(host=socket.gethostname())

    # instantiate worker object
    worker = Worker()

    # register the worker object and generate uri
    uri = daemon.register(worker)

    # get the NODE_NAME environment variable assigned to this container
    node_name = os.getenv('NODE_NAME', default=None)

    if node_name == None:
        print(f"Failed to fetch 'NODE_NAME' environment variable.\n")
        return

    json_env = f"/data/{node_name.lower()}_data.json"

    node_data = {
        "node_name": node_name,
        "uri": str(uri)
    }

    print(f"Worker Node {node_data['node_name']} at URI {node_data['uri']}")

    # write the URI to shared json (env config) file 
    #  this is so the server can automatically fetch worker uris
    with open(json_env, "w", encoding="utf-8") as file:
        json.dump(node_data, file)
        
    daemon.requestLoop()

if __name__ == "__main__":
    main()