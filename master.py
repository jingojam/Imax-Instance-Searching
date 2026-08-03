import Pyro5.api
import os
import json
import pandas as pd
import time
from sklearn.model_selection import train_test_split

# important stuff
#  training/testing split: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html#sklearn.model_selection.train_test_split
#  random foresy: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html

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
            self.results[worker_name] = {}

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
            shuffle=True,
            random_state=42  
        )

    """
        Entry point to Master node
    """
    def Run(self):
        # start with 5% of the training set
        percent = 5
        
        # until 100% of the rows
        while percent < 101:  
            for worker_name, uri in self.workers.items():
                subset = percent/100

                # convert dfs and series to transmittable format (dict), somehow pyro only supports standard types
                #  this can be expensive/slow
                xtr = self.X_train.to_dict(orient='records')
                xte = self.X_test.to_dict(orient='records')
                ytr = self.y_train.to_dict()
                yte = self.y_test.to_dict()

                # obtain a proxy object to the worker
                with Pyro5.api.Proxy(uri) as worker: 
                    self.results[worker_name][f"{percent}%"] = worker.ImaxTrain(xtr, xte, ytr, yte, subset) #RMI
                
                #every 5% increase until 100% of the dataset rows
                percent += 5

        for worker_name, results in self.results.items():
            for result_class, data in results.items():
                print(f"worker: {worker_name}, score={data['score']}, duration: {data['duration']}, subset={data['subset']}%\n{data['report']}")

def main():
    time.sleep(3) # wait 3 seconds to let workers write to their files during startup
    master = Master()
    master.LoadDataset(f"{os.getcwd()}/data/dataset_phishing_trimmed.csv", test_size=0.2, train_size=0.8)
    master.Run()

if __name__ == "__main__":
    main()