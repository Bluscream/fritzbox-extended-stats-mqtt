from datetime import datetime
from time import sleep
from json import loads as json_loads, dumps as json_dumps
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
from asyncio import sleep as sleep_s, run
from dotenv import load_dotenv

from responses.data import Root

load_dotenv()

class FritzBoxStats:
    def __init__(self):
        self.FRITZBOX_IP = getenv('FRITZBOX_IP') or "169.254.1.1"
        self.FRITZBOX_USERNAME = getenv("FRITZBOX_USERNAME") or "sysadmin"
        self.FRITZBOX_PASSWORD = getenv("FRITZBOX_PASSWORD") or ""
        self.FRITZBOX_MODEL = getenv("FRITZBOX_MODEL") or "Fritz!Box 7590"

        self.MQTT_UID_PREFIX = getenv("MQTT_MQTT_UID_PREFIX") or "mqtt_fritzbox_"
        self.MQTT_IP = getenv("MQTT_IP") or ""
        self.MQTT_PORT = getenv("MQTT_PORT") or ""
        self.MQTT_USERNAME = getenv("MQTT_USERNAME") or ""
        self.MQTT_PASSWORD = getenv("MQTT_PASSWORD") or ""

        self.payload = {
            'xhr': '1',
            'lang': 'en',
            'page': 'dslStat',
            'xhrId': 'refresh',
            'useajax': '1',
            'no_sidrenew': '1'
        }
        self.headers = {
            'Accept': "*/*",
            'Accept-Language': "en-US,en;q=0.9",
            'Cache-Control': "no-cache",
            'Connection': "keep-alive",
            'Content-Type': "application/x-www-form-urlencoded",
            'Origin': f"http://{self.FRITZBOX_IP}",
            'Pragma': "no-cache",
            'Referer': f"http://{self.FRITZBOX_IP}/",
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0"
        }
        self.sensor_templates = {
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
        self.sensors = {
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
        self.sensors_published = {}
        self.last_log = ''
        self.mqtt_settings = Settings.MQTT(host=self.MQTT_IP, port=int(self.MQTT_PORT), username=self.MQTT_USERNAME, password=self.MQTT_PASSWORD)
        self.mqtt_device = DeviceInfo(name="Fritz!Box", identifiers="mqtt.fritzbox", model=self.FRITZBOX_MODEL, manufacturer="AVM")
        self.conn = HTTPSConnection(self.FRITZBOX_IP, context=_create_unverified_context())

    def log(self, msg: str, ts: datetime = None):
        if msg == self.last_log: return
        self.last_log = msg
        print(f"{ts or datetime.now()} - {msg}")

    def sanitize(self, name: str) -> str:
        return name.lower().replace('ä','ae').replace('ü','ue').replace('ö','oe').replace(' ','_').replace('.','').replace('(','').replace(')','')

    def get_changes_of_dicts(self, a: dict, b: dict) -> dict:
        if a is None or b is None: return a
        if a.keys() != b.keys(): return a
        changes = {}
        for key in a.keys():
            if a[key] != b[key]: changes[key] = a[key]
        return changes

    def parse_dict(self, d: dict) -> dict:
        for key, val in d.items():
            if isinstance(val, dict): d[key] = self.parse_dict(val)
            elif isinstance(val, str):
                if val.isdigit(): d[key] = int(val)
                elif val.replace('.','',1).isdigit(): d[key] = float(val)
        return d

    def my_callback(self, client: Any, user_data, message: Any):
        self.log(f"Received message: {message.payload.decode('utf-8')}")

    def publish_sensor(self, uid: str, name: str, val: object):
        info = None
        template = {}
        for cat_name, category in self.sensors.items():
            if name in category:
                template = self.sensor_templates[cat_name]
                break
        info = SensorInfo(name=name, device=self.mqtt_device, unique_id=uid, icon=template.get('icon') or None, state_class=template.get('state_class') or None, unit_of_measurement=template.get('unit_of_measurement') or None, device_class=template.get('device_class') or None)
        settings = Settings(mqtt=self.mqtt_settings, entity=info)
        entity = Sensor(settings, self.my_callback)
        self.sensors_published[name] = entity

    def publish_stats(self, vals: dict[str, str]):
        for name, val in vals.items():
            uid = self.MQTT_UID_PREFIX+self.sanitize(name)
            if not name in self.sensors_published.keys(): self.publish_sensor(uid, name, val)
            self.sensors_published[name].set_state(val)

    def get_fritzbox_sid(self):
        global payload
        self.conn.request("GET", "/login_sid.lua")
        response = self.conn.getresponse()
        challenge = ElementTree.fromstring(response.read()).findall(".//Challenge")[0].text
        hash = md5("{}-{}".format(challenge, self.FRITZBOX_PASSWORD).encode("UTF-16LE")).hexdigest()
        response_string = "{}-{}".format(challenge, hash)
        self.conn.request("GET", "/login_sid.lua?username={}&response={}".format(self.FRITZBOX_USERNAME, response_string))
        response = self.conn.getresponse()
        sid = ElementTree.fromstring(response.read()).findall(".//SID")[0].text
        self.log(f"Got new sid: {sid}")
        self.payload['sid'] = sid
        return sid

    def get_stats(self):
        _payload = "&".join([f"{key}={value}" for key, value in self.payload.items()])
        self.conn.request("POST", "/data.lua", _payload, self.headers)
        res = self.conn.getresponse()
        if res.code == 303:
            self.get_fritzbox_sid()
            return self.get_stats()
        txt = res.read()
        utf8 = txt.decode("utf-8")
        try: _json = json_loads(utf8)
        except Exception as e: raise Exception(f"Error parsing json: {utf8}") from e
        _class = Root.from_dict(_json)
        return _class

    async def main(self):
        last_vals = None
        while True:
            try:
                stats = self.get_stats()
                vals = stats.data.get_all_values()
                changed = self.get_changes_of_dicts(vals, last_vals)
                if len(changed.keys()) < 1:
                    self.log("No changes")
                    continue
                last_vals = vals
                self.publish_stats(self.parse_dict(changed))
            except Exception as e:
                self.log(f"Error: {e}")
                try: await sleep_s(10)
                except: sleep(10)

if __name__ == "__main__":
    fritzBoxStats = FritzBoxStats()
    if (len(argv) > 1): sid = argv[1]
    run(fritzBoxStats.main())
