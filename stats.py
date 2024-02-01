from datetime import datetime
from json import loads as json_loads
# from json import dumps as json_dumps
from xml.etree import ElementTree
from hashlib import md5
from sys import argv
from ssl import _create_unverified_context
from os import getenv


import paho.mqtt.client as mqtt
from http.client import HTTPSConnection, HTTPConnection
from asyncio import sleep as sleep_s # from time import sleep
from asyncio import run
from dotenv import load_dotenv

from responses.data import Root

# get MQTT_HOST from dotenv

load_dotenv()
payload = {
    'xhr': '1',
    'lang': 'en',
    'page': 'dslStat',
    'xhrId': 'refresh',
    'useajax': '1',
    'no_sidrenew': '1'
}
headers = {
    'Accept': "*/*",
    'Accept-Language': "en-US,en;q=0.9",
    'Cache-Control': "no-cache",
    'Connection': "keep-alive",
    'Content-Type': "application/x-www-form-urlencoded",
    'Origin': f"http://{getenv('FRITZBOX_IP')}",
    'Pragma': "no-cache",
    'Referer': f"http://{getenv('FRITZBOX_IP')}/",
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0"
    }

last_log = ''
def log(msg: str, ts: datetime = None):
    global last_log
    if msg == last_log: return
    last_log = msg
    print(f"{ts or datetime.now()} - {msg}")
def sanitize(name: str) -> str:
    return name.replace(" ", "-").replace(".", "_")
def dicts_are_different(a: dict, b: dict) -> bool:
    if a is None or b is None: return True
    if a.keys() != b.keys(): return True
    for key in a.keys():
        if a[key] != b[key]: return True
    return False

mqtt_client = mqtt.Client()
mqtt_client.connect(getenv("MQTT_IP"), int(getenv("MQTT_PORT")), 60)
mqtt_client.loop_start()
mqtt_client.username_pw_set(getenv("MQTT_USERNAME"), getenv("MQTT_PASSWORD"))
def publish_stats(vals: dict[str, str]):
    for name, val in vals.items():
        mqtt_client.publish(f'fritzbox_extended/{sanitize(name)}', val)


conn = HTTPSConnection(
    getenv("FRITZBOX_IP"),
    context = _create_unverified_context()
)
def get_fritzbox_sid():
    global payload
    conn.request("GET", "/login_sid.lua")
    response = conn.getresponse()
    challenge = ElementTree.fromstring(response.read()).findall(".//Challenge")[0].text
    hash = md5("{}-{}".format(challenge, getenv("FRITZBOX_PASSWORD")).encode("UTF-16LE")).hexdigest()
    response_string = "{}-{}".format(challenge, hash)
    conn.request("GET", "/login_sid.lua?username={}&response={}".format(getenv("FRITZBOX_USERNAME"), response_string))
    response = conn.getresponse()
    sid = ElementTree.fromstring(response.read()).findall(".//SID")[0].text
    # conn.close()
    log(f"Got new sid: {sid}")
    payload['sid'] = sid
    return sid

def get_stats():
    _payload = "&".join([f"{key}={value}" for key, value in payload.items()])
    conn.request("POST", "/data.lua", _payload, headers)
    res = conn.getresponse()
    if res.code == 303:
        get_fritzbox_sid()
        return get_stats()
    txt = res.read()
    utf8 = txt.decode("utf-8")
    try: _json = json_loads(utf8)
    except Exception as e: raise Exception(f"Error parsing json: {utf8}") from e
    _class = Root.from_dict(_json)
    return _class

async def main():
    last_vals = None
    while True:
        try:
            stats = get_stats()
            vals = stats.data.get_all_values() # .get_values(important_values)
            if not dicts_are_different(vals, last_vals):
                log("No change")
                continue
            # for name, val in vals.items():
            #     log(f"{name}: {val}")
            log(f"DSLAM: {vals['DSLAM-Datenrate Min.']} / {vals['DSLAM-Datenrate Max.']} kbit/s (Cable: {vals['Leitungskapazität']} kbit/s | ~{vals['ungefähre Leitungslänge']}m)")
            publish_stats(vals)
        except Exception as e: log(f"Error: {e}")
        await sleep_s(10)

if __name__ == "__main__":
    if (len(argv) > 1): sid = argv[1]
    run(main())