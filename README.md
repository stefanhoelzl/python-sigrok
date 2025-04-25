# python-sigrok

Python-API for [libsigrok](https://sigrok.org/wiki/Libsigrok)

## Installation
```bash
pip install pip install sigrok@git+https://github.com/stefanhoelzl/python-sigrok/
```

### Requirements
#### Ubuntu
```bash
apt install libsigrok4 libsigrok-dev
```

### Fedora
```bash
dnf install libsigrok libsigrok-devel
```

#### macOS
```bash
brew install libsigrok
```

#### Windows
pre-built libsigrok dlls are shipped with this package.

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
