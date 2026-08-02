import Pyro5.api
import asyncio
import os
import json
import glob

class Master:
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
                with open(path, 'r', encoding='utf-8') as file:
                    node_data = json.load(file)
                    self.nodes[node_id] = node_data

                node_id += 1
            except FileNotFoundError:
                print(f"File error: couldn't find {json_env}.\n")
                return

        for id, data in node_configs.items():
            self.nodes[id]['proxy'] = Pyro5.api.Proxy(self.nodes[id]['uri'])

    def StartScheduler(self):
        # flow is something like (assuming Train() RPC generates a random forest and writes ):
        #   random_forest = self.nodes[self.current_node].ImaxTrain(start_instance, end_instance)
        #   self.nodes[self.current_node]['forest'] = random_forest
        #       then testing on 20% of dataset...
        pass

async def main():
    await asyncio.sleep(3000) # wait 3 seconds to let workers write to their files during startup
    master = Master()

if __name__ == "__main__":
    asyncio.run(main())