import Pyro5.api
import asyncio
import os
import json
import glob
import pandas as pd
from sklearn.model_selection import train_test_split

# important stuff
#  training/testing split: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html#sklearn.model_selection.train_test_split
#  random foresy: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html

class Master:
    """
        Default constructor
    """
    def __init__(self):
        self.current_node = 0
        self.nodes = {}
        node_id = 0

        # since all workers write their node info to their own data file
        #  load every file in /data (of pattern *_data.json)
        filename_pattern = os.path.join('/data', '*_data.json')

        # enumerate file paths to each file
        paths = glob.glob(filename_pattern)

        # then load each
        for path in paths:
            # check if config file exists
            try:
                with open(path, "r", encoding="utf-8") as file:
                    node_data = json.load(file)
                    self.nodes[node_id] = node_data

                node_id += 1
            except FileNotFoundError:
                print(f"File error: couldn't find {json_env}.\n")
                return

        for id, data in self.nodes.items():
            self.nodes[id]['proxy'] = Pyro5.api.Proxy(self.nodes[id]['uri'])
            print(f"Connected to Worker Node {self.nodes[id]['node_name']} at URI {self.nodes[id]['uri']}")

    """
        Loads dataset from disk and splits it to training and testing (80%/20% default)
    """
    def LoadDataset(self, dataset, test_size=0.2, train_size=0.8):
        df = pd.read_csv(dataset)
        self.X = df.drop(columns=['url', 'label', 'tld'], inplace=True)
        self.y = df['label']

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            self.dataset,
            test_size=test_size,
            train_size=train_size,
            shuffle=True,
            random_state=42  
        )

    """
        Moves pointer to the next node, and sets it to current
        Returns id of the new current node
    """
    def NextNode(self):
        self.current_node = (self.current_node + 1) % 5
        return self.current_node

    """
        Entry point to Master node
    """
    def Run(self):

        pass

async def main():
    await asyncio.sleep(3) # wait 3 seconds to let workers write to their files during startup
    master = Master()
    master.LoadDataset('/data/phishing_features.csv', test_size=0.2, train_size=0.8)
    master.Run()

if __name__ == "__main__":
    asyncio.run(main())