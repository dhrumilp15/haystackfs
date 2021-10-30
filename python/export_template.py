from urllib import request
import os


root_dir = "discordfs-export"
headers = {
    "User-Agent": "discordfs/1.0"
}

files = [

]

if not os.path.exists(root_dir):
    os.mkdir(root_dir)

for f in files:
    path = os.path.join(root_dir, f["channel_name"], f["filename"])
    if os.path.exists(path):
        f"Skipping {f['url']} (already downloaded)"
        continue
    print(f"Fetching {f['url']}")
    req = request.Request(f["url"], {}, headers)
    with request.urlopen(req) as url:
        if url.status == 429:
            print("Timeout")
        b = url.read()
        if not os.path.exists(os.path.join(root_dir, f["channel_name"])):
            os.mkdir(os.path.join(root_dir, f["channel_name"]))
        path = os.path.join(path)
        with open(path, "wb") as out:
            out.write(b)

