import Pyro5.api
import asyncio
import os
import json

@Pyro5.api.expose
class Worker:
    def __init(self):
        pass

    """
        Method for training (from start_instance row, to last_instance row).
        Returns a generated Random Forest for the batch
    """
    def ImaxTrain(self, start_instance, last_instance):
        pass

def main():
    # create a pyro daemon for dispatching rpc
    #  use wildcard address to automatically resolve to specific container
    daemon = Pyro5.api.Daemon(host='0.0.0.0')

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

    # write the URI to shared json (env config) file 
    #  this is so the server can automatically fetch worker uris
    with open(json_env, 'w', encoding='utf-8') as file:
        json.dump(node_data, file)
        
    daemon.requestLoop()

if __name__ == "__main__":
    main()