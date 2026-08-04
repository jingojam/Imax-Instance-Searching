import Pyro5.api
import Pyro5.errors
import os
import sys
import json
import pandas as pd
import time
import threading
import queue
from sklearn.model_selection import train_test_split
from kneed import KneeLocator

#set pyro connection timeout to 5 seconds
Pyro5.config.COMMTIMEOUT = 5.0

# important stuff
#  training/testing split: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html#sklearn.model_selection.train_test_split
#  random foresy: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html

OUTPUT = f"{os.getcwd()}/data/imax_results.json"
DATASET = f"{os.getcwd()}/data/dataset_phishing_trimmed.csv"
PERCENT = 5   # starting subset of instances to feed to the workers
INCREMENT = 5 # increments (5%, 10%, etc.)

#shared data lock
DATA_LOCK = threading.Lock()

class Master:
    """
        Default constructor
    """
    def __init__(self, ns):
        self.results = {}
        self.task_queue = queue.Queue()
        name_server = Pyro5.api.locate_ns(ns)

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
        Background thread for RMI
    """
    def DoWork(self, worker_name, uri, xtr, xte, ytr, yte):
        #  this background thread will run until no more subsets to train on
        while True:
            try:
                # get subset from the queue
                percent = self.task_queue.get_nowait()
            except queue.Empty:
                return
            
            subset = percent/100

            # obtain a proxy object to the worker
            try:
                with Pyro5.api.Proxy(uri) as worker:
                    name = worker_name.removeprefix("workers.")
                    result = worker.ImaxTrain(xtr, xte, ytr, yte, subset) #RMI

                    with DATA_LOCK: # critical section, so lock the shared resource when adding new keys
                        self.results[name][percent] = result
            except (Pyro5.errors.CommunicationError, Pyro5.errors.TimeoutError, Pyro5.errors.ConnectionClosedError): # catch all these stuff = failed to communicate with worker
                    print(f"Connection to Worker {worker_name} unexpectedly failed.\n")
                    # move to the next worker available
                    #  use the same subset for the next worker (all-or-nothing for worker)
                    with DATA_LOCK:
                        # remove the worker if connection is dropped
                        if worker_name in self.workers:
                            del self.workers[worker_name]
                    self.task_queue.put(percent)
                    return
            finally:
                # done processing
                self.task_queue.task_done()

    """
        Entry point to Master node
    """
    def Run(self):
        # start with % of the training set
        percent = PERCENT

        #use every subset as tasks
        while percent < 101:
            self.task_queue.put(percent)
            percent += INCREMENT
        
        # convert dfs and series to transmittable format (dict), somehow pyro only supports standard types
        #  this can be expensive/slow
        xtr = self.X_train.to_dict(orient='records')
        xte = self.X_test.to_dict(orient='records')
        ytr = self.y_train.to_dict()
        yte = self.y_test.to_dict()

        # create threads for every worker
        threads = []
        for worker_name, uri in self.workers.items():
            threads.append(threading.Thread(target=self.DoWork, args=(worker_name, uri, xtr, xte, ytr, yte)))
            
        # start each thread
        for thread in threads:
            thread.start()

        # then clean all threads
        for thread in threads:
            thread.join()

        # write to the results output
        with open(OUTPUT, "w", encoding="utf-8") as file:
            json.dump(self.results, file, indent=2)

        subsets = []
        train_times = []
        scores = []

        # get the 
        for node_name, data in self.results.items():
            for subset, node_results in data.items():
                scores.append(node_results['score'])
                train_times.append(node_results['duration'])
                subsets.append(int(subset))
        
        #create a table (subset, training time, and score as columns)
        df = pd.DataFrame(
            {
                'subset': subsets,
                'train_time': train_times,
                'score': scores
            }
        )

        # sort the table based on subset
        df = df.sort_values('subset')

        # find knee (elbow) point between training time and score
        kl = KneeLocator(df['train_time'], df['score'], curve="concave", direction="increasing")

        # these are the "best" training time and score
        optimal_train_time = kl.knee
        optimal_score = kl.knee_y

        optimal_subset = -1
        optimal_scores = None
        worker_assigned = None

        # find the subset that has these train time and score
        for node_name, data in self.results.items():
            for subset, node_results in data.items():
                if node_results['score'] == optimal_score and node_results['duration'] == optimal_train_time:
                    optimal_subset = subset
                    optimal_scores = node_results['report']
                    worker_assigned = node_name
                    break

        print(f"Optimal subset:\n")
        print(f"\tworker: {worker_assigned}\n\tsubset={optimal_subset}%:\n\ttraining time={optimal_train_time}\n\taccuracy={optimal_score}\n\tscores:")

        print(f"\t\t0:")
        print(f"\t\t\tprecision={optimal_scores['0']['precision']}")
        print(f"\t\t\trecall={optimal_scores['0']['recall']}")
        print(f"\t\t\tf1-score={optimal_scores['0']['f1-score']}")
        print(f"\t\t\tsupport={optimal_scores['0']['support']}\n")

        print(f"\t\t1:")
        print(f"\t\t\tprecision={optimal_scores['1']['precision']}")
        print(f"\t\t\trecall={optimal_scores['1']['recall']}")
        print(f"\t\t\tf1-score={optimal_scores['1']['f1-score']}")
        print(f"\t\t\tsupport={optimal_scores['1']['support']}\n")

        print(f"\t\tmacro average:")
        print(f"\t\t\tprecision={optimal_scores['macro avg']['precision']}")
        print(f"\t\t\trecall={optimal_scores['macro avg']['recall']}")
        print(f"\t\t\tf1-score={optimal_scores['macro avg']['f1-score']}")
        print(f"\t\t\tsupport={optimal_scores['macro avg']['support']}\n")

        print(f"\t\tweighted average:")
        print(f"\t\t\tprecision={optimal_scores['weighted avg']['precision']}")
        print(f"\t\t\trecall={optimal_scores['weighted avg']['recall']}")
        print(f"\t\t\tf1-score={optimal_scores['weighted avg']['f1-score']}")
        print(f"\t\t\tsupport={optimal_scores['weighted avg']['support']}")

def main(ns="nameserver"):
    time.sleep(3) # wait 3 seconds to let workers write to their files during startup
    master = Master(ns)
    master.LoadDataset(DATASET, test_size=0.2, train_size=0.8)
    master.Run()

if __name__ == "__main__":
    mode = None
    ns = None

    if len(sys.argv) > 1:
        mode = sys.argv[1]

    # if mode is containerized (via docker)
    if mode == "containerized":
        ns = "nameserver" # nameserver is the name assigned to nameserver container
    elif mode is None or mode == "raw":
        ns = None # if no argument or "raw" mode

    main(ns)