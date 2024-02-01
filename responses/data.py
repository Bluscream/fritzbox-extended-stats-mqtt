from typing import Optional, List, Union, Any

class ValClass:
    us: Optional[str]
    ds: str

    def __init__(self, us: Optional[str], ds: str) -> None:
        self.us = us
        self.ds = ds

    @classmethod
    def from_dict(cls, json: dict):
        us = json['us'] if 'us' in json else None
        ds = json['ds']
        return cls(us, ds)

class ErrorCounter:
    title: str
    val: Optional[List[ValClass]]

    def __init__(self, title: str, val: Optional[List[ValClass]]) -> None:
        self.title = title
        self.val = val

    @classmethod
    def from_dict(cls, json: dict):
        title = json['title']
        val = [ValClass.from_dict(v) for v in json['val']] if 'val' in json else []
        return cls(title, val)

class NegotiatedValue:
    unit: Optional[str]
    title: str
    val: Optional[List[Union[ValClass, str]]]

    def __init__(self, unit: Optional[str], title: str, val: Optional[List[Union[ValClass, str]]]) -> None:
        self.unit = unit
        self.title = title
        self.val = val

    @classmethod
    def from_dict(cls, json: dict):
        unit = json['unit'] if 'unit' in json else None
        title = json['title']
        val = [ValClass.from_dict(v) if isinstance(v, dict) else v for v in json['val']] if 'val' in json else []
        return cls(unit, title, val)

class Data:
    is_connected: bool
    negotiated_values: List[NegotiatedValue]
    error_counters: List[ErrorCounter]
    data_type: str

    def __init__(self, is_connected: bool, negotiated_values: List[NegotiatedValue], error_counters: List[ErrorCounter], data_type: str) -> None:
        self.is_connected = is_connected
        self.negotiated_values = negotiated_values
        self.error_counters = error_counters
        self.data_type = data_type

    def get_all_values(self) -> dict[str, str]:
        vals = {}
        for val in self.negotiated_values:
            if (len(val.val) > 0): vals[val.title] = val.val[0].ds if hasattr(val.val[0], "ds") else val.val[0]
        return vals

    def get_values(self, names: list[str]) -> dict[str, str]:
        return {name: self.get_value(name) for name in names}

    def get_value(self, name: str) -> Optional[str]:
        return self.get_negotiated_value(name)[0].ds

    def get_negotiated_value(self, name: str) -> Optional[List[ValClass]]:
        for val in self.negotiated_values:
            if val.title == name:
                return val.val
        return None
    
    def get_error_counter(self, name: str) -> Optional[List[ValClass]]:
        for val in self.error_counters:
            if val.title == name:
                return val.val
        return None

    @classmethod
    def from_dict(cls, json: dict):
        is_connected = json['isConnected']
        negotiated_values = [NegotiatedValue.from_dict(n) for n in json['negotiatedValues']]
        error_counters = [ErrorCounter.from_dict(e) for e in json['errorCounters']]
        data_type = json['type'] if 'type' in json else None
        return cls(is_connected, negotiated_values, error_counters, data_type)


class Hide:
    prov_serv: bool
    sso_set: bool
    rrd: bool

    def __init__(self, prov_serv: bool, sso_set: bool, rrd: bool) -> None:
        self.prov_serv = prov_serv
        self.sso_set = sso_set
        self.rrd = rrd

    @classmethod
    def from_dict(cls, json: dict):
        prov_serv = json['provServ']
        sso_set = json['ssoSet']
        rrd = json['rrd']
        return cls(prov_serv, sso_set, rrd)


class Root:
    pid: str
    hide: Hide
    time_till_logout: int
    time: List[Any]
    data: Data
    sid: str

    def __init__(self, pid: str, hide: Hide, time_till_logout: int, time: List[Any], data: Data, sid: str) -> None:
        self.pid = pid
        self.hide = hide
        self.time_till_logout = time_till_logout
        self.time = time
        self.data = data
        self.sid = sid

    @classmethod
    def from_dict(cls, json: dict):
        pid = json['pid']
        hide = Hide.from_dict(json['hide'])
        time_till_logout = json['timeTillLogout']
        time = json['time']
        data = Data.from_dict(json['data'])
        sid = json['sid']
        return cls(pid, hide, time_till_logout, time, data, sid)