import requests.exceptions
from requests import get, post
from queue import Queue
from io import BytesIO


def getpic(queue: Queue, thread_id, content=None):
    url = "https://api.lolicon.app/setu/v2"
    try:
        r = post(url, json=content, timeout=5).json()
        print("Get Meta Finished!")
    except (requests.exceptions.SSLError, requests.exceptions.ReadTimeout):
        return "error"
    else:
        if not r.get("error"):
            meta = r["data"][0]
            try:
                print("Thread #%d Getting Pictures" % thread_id)
                resp = get(meta["urls"]["original"], stream=True)
                total = int(resp.headers.get('content-length', 1024*1024))
                print(meta["urls"]["original"])
                print(total)
                fp = BytesIO()
                size = 0
                for data in resp.iter_content(chunk_size=16384):
                    size += fp.write(data)
                    queue.put("线程#%d正在下载:%d%%" % (thread_id, 100*(size/total)))
                fp.seek(0)
                pic = fp.read()
                fp.close()
            except (requests.exceptions.SSLError, requests.exceptions.ReadTimeout):
                return "error"
            else:
                if resp.status_code == 404:
                    return "not_found"
                return meta, pic
        else:
            return "error"
