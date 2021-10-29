from urllib import request
import os


headers = {
    "User-Agent": "discordfs/1.0"
}

files = [

]

for f in files:
    req = request.Request(f["url"], {}, headers)
    with request.urlopen(req) as url:
        b = url.read()
        if not os.path.exists(f["channel_name"]):
            os.mkdir(f["channel_name"])
            path = os.path.join(f["channel_name"], f["filename"])
            with open(path, "wb") as out:
                out.write(b)

