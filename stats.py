import http.client
from .responses.data import Root

payload = "xhr=1&sid=d94b7663ac22e56c&lang=en-US&page=dslStat&xhrId=refresh&useajax=1&no_sidrenew=1"
headers = {
    'Accept': "*/*",
    'Accept-Language': "en-US,en;q=0.9",
    'Cache-Control': "no-cache",
    'Connection': "keep-alive",
    'Content-Type': "application/x-www-form-urlencoded",
    'Origin': "http://192.168.2.1",
    'Pragma': "no-cache",
    'Referer': "http://192.168.2.1/",
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    'x-request-modified': "1"
    }

conn = http.client.HTTPConnection("192.168.2.1")
conn.request("POST", "/data.lua", payload, headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))