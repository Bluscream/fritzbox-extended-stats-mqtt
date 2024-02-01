from typing import List
from typing import Any
from dataclasses import dataclass
import json
@dataclass
class Data:
    isConnected: bool
    negotiatedValues: List[NegotiatedValue]
    errorCounters: List[ErrorCounter]
    dataType: str

    @staticmethod
    def from_dict(obj: Any) -> 'Data':
        _isConnected = 
        _negotiatedValues = [NegotiatedValue.from_dict(y) for y in obj.get("negotiatedValues")]
        _errorCounters = [ErrorCounter.from_dict(y) for y in obj.get("errorCounters")]
        _dataType = str(obj.get("dataType"))
        return Data(_isConnected, _negotiatedValues, _errorCounters, _dataType)

@dataclass
class ErrorCounter:
    title: str
    val: List[Val]

    @staticmethod
    def from_dict(obj: Any) -> 'ErrorCounter':
        _title = str(obj.get("title"))
        _val = [Val.from_dict(y) for y in obj.get("val")]
        return ErrorCounter(_title, _val)

@dataclass
class Hide:
    provServ: bool
    ssoSet: bool
    rrd: bool

    @staticmethod
    def from_dict(obj: Any) -> 'Hide':
        _provServ = 
        _ssoSet = 
        _rrd = 
        return Hide(_provServ, _ssoSet, _rrd)

@dataclass
class NegotiatedValue:
    unit: str
    title: str
    val: List[object]

    @staticmethod
    def from_dict(obj: Any) -> 'NegotiatedValue':
        _unit = str(obj.get("unit"))
        _title = str(obj.get("title"))
        _val = [.from_dict(y) for y in obj.get("val")]
        return NegotiatedValue(_unit, _title, _val)

@dataclass
class Root:
    pid: str
    hide: Hide
    timeTillLogout: str
    time: List[object]
    data: Data
    sid: str

    @staticmethod
    def from_dict(obj: Any) -> 'Root':
        _pid = str(obj.get("pid"))
        _hide = Hide.from_dict(obj.get("hide"))
        _timeTillLogout = str(obj.get("timeTillLogout"))
        _time = [.from_dict(y) for y in obj.get("time")]
        _data = Data.from_dict(obj.get("data"))
        _sid = str(obj.get("sid"))
        return Root(_pid, _hide, _timeTillLogout, _time, _data, _sid)

@dataclass
class Val:
    us: str
    ds: str

    @staticmethod
    def from_dict(obj: Any) -> 'Val':
        _us = str(obj.get("us"))
        _ds = str(obj.get("ds"))
        return Val(_us, _ds)

# Example Usage
# jsonstring = json.loads(myjsonstring)
# root = Root.from_dict(jsonstring)
