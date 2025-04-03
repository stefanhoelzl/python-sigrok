# python-sigrok

Python-API for [libsigrok](https://sigrok.org/wiki/Libsigrok)

## Installation
```bash
pip install pip install sigrok@git+https://github.com/stefanhoelzl/python-sigrok/
```

## Usage
```python
from sigrok import Sigrok, Device, Packet, LogicPacket

logic_packets = []

def cb(dev: Device, packet: Packet):
    print(f"{dev.model} recorded {packet}")
    if isinstance(packet, LogicPacket):
        logic_packets.append(packet)
    return len(logic_packets) < 10


with (
    Sigrok() as sr,
    sr.get_driver("demo") as driver,
    driver.scan()[0] as device
):
    device.enable_channels("D0")
    sr.run(cb, [device])
```

## Requirements
### Ubuntu/Debian
```bash
apt-get install libsigrok4 libsigrok-dev pkgconf
```

### Fedora
```bash
dnf install libsigrok libsigrok-devel pkgconf
```
