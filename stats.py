from datetime import datetime
from time import sleep
from json import loads as json_loads
from json import dumps as json_dumps
from xml.etree import ElementTree
from hashlib import md5
from sys import argv
from ssl import _create_unverified_context
from os import getenv
from typing import Any, Optional
from sys import maxsize

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import SensorInfo, Sensor, DeviceInfo
from http.client import HTTPSConnection, HTTPConnection
from asyncio import sleep as sleep_s # from time import sleep
from asyncio import run
from dotenv import load_dotenv

from responses.data import Root



load_dotenv()
uid_prefix = getenv("MQTT_UID_PREFIX") or "mqtt_fritzbox_"
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
sensor_templates = {
    "kbits": {
        'state_class': 'measurement',
        'unit_of_measurement': 'kB/s',
        'device_class': 'data_rate',
        'icon': 'mdi:speedometer'
    },
    "meters": {
        'state_class': 'measurement',
        'unit_of_measurement': 'm',
        'device_class': 'length',
        'icon': 'mdi:ruler'
    },
    "ms": {
        'state_class': 'measurement',
        'unit_of_measurement': 'ms',
        'device_class': 'duration',
        'icon': 'mdi:timer'
    },
}
"""
"DSLAM-Datenrate Max.",
"DSLAM-Datenrate Min.",
"Leitungskapazität",
"Aktuelle Datenrate",
"Min Effektive Datenrate",
"Nahtlose Ratenadaption",
"Trägertausch (Bitswap)",
"Latenz",
"Impulsstörungsschutz (INP)",
"G.INP",
"Störabstandsmarge",
"Leitungsdämpfung",
"ungefähre Leitungslänge",
"Profil",
"G.Vector",
"Trägersatz",
"Sekunden mit",
"Fehlern (ES)",
"Fehlern (SES)",
"Nicht behebbare Fehler (CRC)",
"pro Minute",
"letzte 15 Minuten",
"korrigierte DTU",
"pro Minute",
"letzte 15 Minuten",
"unkorrigierte DTU",
"pro Minute",
"letzte 15 Minuten"
"""
sensors = {
    "kbits": [
        "DSLAM-Datenrate Max.",
        "DSLAM-Datenrate Min.",
        "Leitungskapazität",
        "Aktuelle Datenrate",
        "Min Effektive Datenrate",
    ],
    "meters": [
        "ungefähre Leitungslänge"
    ],
    "ms": [
        "Latenz"
    ]
}
sensors_published = {}

last_log = ''
def log(msg: str, ts: datetime = None):
    global last_log
    if msg == last_log: return
    last_log = msg
    print(f"{ts or datetime.now()} - {msg}")
def sanitize(name: str) -> str:
    return name.lower().replace('ä','ae').replace('ü','ue').replace('ö','oe').replace(' ','_').replace('.','').replace('(','').replace(')','') # .join([c for c in name if ord(c) < 128 or c == '_']).lower()
def is_number(val: object) -> bool: return isinstance(val, int) or isinstance(val, float)
# def dicts_are_different(a: dict, b: dict) -> bool:
#     if a is None or b is None: return True
#     if a.keys() != b.keys(): return True
#     for key in a.keys():
#         if isinstance(a[key], dict) and isinstance(b[key], dict):
#             if dicts_are_different(a[key], b[key]): return True
#         if a[key] != b[key]: return True
#     return False
def get_changes_of_dicts(a: dict, b: dict) -> dict:
    if a is None or b is None: return a
    if a.keys() != b.keys(): return a
    changes = {}
    for key in a.keys():
        if isinstance(a[key], dict) and isinstance(b[key], dict):
            changes[key] = get_changes_of_dicts(a[key], b[key])
        if a[key] != b[key]: changes[key] = a[key]
    return changes
def parse_dict(d: dict) -> dict:
    for key, val in d.items():
        if isinstance(val, dict): d[key] = parse_dict(val)
        elif isinstance(val, str):
            if val.isdigit(): d[key] = int(val)
            elif val.replace('.','',1).isdigit(): d[key] = float(val)
    return d

mqtt_settings = Settings.MQTT(host=getenv("MQTT_IP"), port=int(getenv("MQTT_PORT")), username=getenv("MQTT_USERNAME"), password=getenv("MQTT_PASSWORD"), )
mqtt_device = DeviceInfo(name="Fritz!Box", identifiers="mqtt.fritzbox", model="Fritz!Box 7590", manufacturer="AVM")

def my_callback(client: Any, user_data, message: Any): pass

def publish_sensor(uid: str, name: str, val: object):
    info = None
    is_num = is_number(val)
    log(f'name: {name} | isnum: {is_num} | type: {type(val)}')
    template = {}
    for cat_name, category in sensors.items():
        if name in category:
            template = sensor_templates[cat_name]
            break
    info = SensorInfo(name=name, device=mqtt_device, unique_id=uid, icon=template.get('icon') or None, state_class=template.get('state_class') or None, unit_of_measurement=template.get('unit_of_measurement') or None, device_class=template.get('device_class') or None)
    settings = Settings(mqtt=mqtt_settings, entity=info)
    entity = None
    entity = Sensor(settings, my_callback)
    sensors_published[name] = entity
def publish_stats(vals: dict[str, str]):
    for name, val in vals.items():
        uid = uid_prefix+sanitize(name)
        if not name in sensors_published.keys(): publish_sensor(uid, name, val)
        sensors_published[name].set_state(val)


conn = HTTPSConnection(getenv("FRITZBOX_IP"),context = _create_unverified_context())
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
        # try:
            stats = get_stats()
            vals = stats.data.get_all_values() # .get_values(important_values)
            changed = get_changes_of_dicts(vals, last_vals)
            if len(changed) < 1:
                log("No changes")
                continue
            last_vals = vals
            log(f"Changes: {changed}")
            # log(f"DSLAM: {vals['DSLAM-Datenrate Min.']} / {vals['DSLAM-Datenrate Max.']} kbit/s (Cable: {vals['Leitungskapazität']} kbit/s | ~{vals['ungefähre Leitungslänge']}m)")
            publish_stats(parse_dict(changed))
        # except Exception as e:
        #     log(f"Error: {e}")
            try: await sleep_s(10)
            except: sleep(10)

if __name__ == "__main__":
    if (len(argv) > 1): sid = argv[1]
    run(main())