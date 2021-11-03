from typing import List, Dict

template_top = """
#!/usr/bin/env python3

# This script will download all the files you requested.
# To run it, you will need Python 3 installed on your computer.
# For Windows, you can install it from the MS store, or from
# https://www.python.org/downloads/windows/
# For macOS, you can install it from https://www.python.org/downloads/macos/
# For Linux, use your distor's package manager.
# If you need help running the script, see
# https://realpython.com/run-python-scripts/#how-to-run-python-scripts-using-the-command-line

from http import HTTPStatus
from urllib import request
import json
import os
from time import sleep


root_dir = "discordfs-export"
headers = {
    "User-Agent": "discordfs/1.0"
}

files = ["""
template_bottom = """]

if not os.path.exists(root_dir):
    os.mkdir(root_dir)

for f in files:
    path = os.path.join(root_dir, str(f["channel_id"]), f["file_name"])
    if os.path.exists(path):
        print(f"Skipping {f['url']} (already downloaded)")
        continue
    print(f"Fetching {f['url']}")
    finished = False
    while not finished:
        req = request.Request(f["url"], {}, headers)
        with request.urlopen(req) as url:
            if url.status == HTTPStatus.TOO_MANY_REQUESTS:
                retry_after = json.loads(url.body)["retry_after"]
                print(f"Being rate limited, waiting for {retry_after} seconds")
                sleep(retry_after)
                continue
            elif url.status != HTTPStatus.OK:
                print(f"Error: HTTP request returned {url.status}")
                finished = True
                continue
            b = url.read()
            if not os.path.exists(os.path.join(root_dir, str(f["channel_id"]))):
                os.mkdir(os.path.join(root_dir, str(f["channel_id"])))
            path = os.path.join(path)
            with open(path, "wb") as out:
                out.write(b)
            finished = True
"""

def generate_script(files: List[Dict]) -> str:
    """Generates the contents of a script file."""
    dict_strs = list(map(lambda d: str(d) + ',', files))
    return template_top + '\n'.join(dict_strs) + template_bottom
