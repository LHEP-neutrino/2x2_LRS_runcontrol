import json
import requests

with open("example_run_config.json") as json_data:
    test = json.load(json_data)
print(test)
requests.post("http://192.168.197.45:5051/api/start_data_run/",json=test)

