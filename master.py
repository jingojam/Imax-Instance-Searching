import Pyro5.api
import Pyro5.errors
import os
import json
import pandas as pd
import time
from sklearn.model_selection import train_test_split

# important stuff
#  training/testing split: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html#sklearn.model_selection.train_test_split
#  random foresy: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html

OUTPUT = f"{os.getcwd()}/data/imax_results.json"
DATASET = f"{os.getcwd()}/data/dataset_phishing_trimmed.csv"
PERCENT = 5   # starting subset of instances to feed to the workers
INCREMENT = 5 # increments (5%, 10%, etc.)

class Master:
    """
        Default constructor
    """
    def __init__(self):
        self.results = {}
        name_server = Pyro5.api.locate_ns("nameserver")

        print()
        
        #get dict of workers registered to the nameserver
        self.workers = name_server.list(prefix="workers.")
        print(f"Available workers registered to Name Server: {len(self.workers)} worker nodes.")

        # initialize results dict with worker keys
        for worker_name, uri in self.workers.items():
            print(f"Found worker {worker_name}, URI: {uri}")
            name = worker_name.removeprefix("workers.")
            self.results[name] = {}

        print()

    """
        Loads dataset from disk and splits it to training and testing (80%/20% default)
    """
    def LoadDataset(self, dataset, test_size=0.2, train_size=0.8):
        df = pd.read_csv(dataset)
        # HERE this might be wrong, assumed 'status' column is the results to train on
        self.X = df.drop(columns=['status'])
        self.y = df['status']

        # split dataset into training (80%) and testing (20%) splits
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            self.X, self.y,
            test_size=test_size,
            train_size=train_size,
            stratify=self.y,
            random_state=42  
        )

    """
        Entry point to Master node
    """
    def Run(self):
        # start with % of the training set
        percent = PERCENT
        
        # until 100% of the rows
        while percent < 101:  
            # convert dfs and series to transmittable format (dict), somehow pyro only supports standard types
            #  this can be expensive/slow
            xtr = self.X_train.to_dict(orient='records')
            xte = self.X_test.to_dict(orient='records')
            ytr = self.y_train.to_dict()
            yte = self.y_test.to_dict()
            
            #cycle through every worker (round-robin)
            for worker_name, uri in self.workers.items():
                if percent > 100:
                    break

                subset = percent/100

                # obtain a proxy object to the worker
                with Pyro5.api.Proxy(uri) as worker:
                    try:
                        name = worker_name.removeprefix("workers.")
                        self.results[name][percent] = worker.ImaxTrain(xtr, xte, ytr, yte, subset) #RMI
                    except Pyro5.errors.CommunicationError: # failed to communicate with worker
                        print(f"Connection to Worker {worker_name} unexpectedly failed.\n")
                        # move to the next worker available
                        #  use the same subset for the next worker (all-or-nothing for worker)
                        continue

                #every % increase until 100% of the dataset rows
                percent += INCREMENT

        # write to the results output
        with open(OUTPUT, "w", encoding="utf-8") as file:
            json.dump(self.results, file, indent=2)

def main():
    time.sleep(3) # wait 3 seconds to let workers write to their files during startup
    master = Master()
    master.LoadDataset(DATASET, test_size=0.2, train_size=0.8)
    master.Run()

if __name__ == "__main__":
    main()