# python-sigrok

Python-API for [libsigrok](https://sigrok.org/wiki/Libsigrok)

## Installation
```bash
pip install -i https://test.pypi.org/simple/ sigrok
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
from sigrok import Sigrok, Device, Packet, LogicPacket, ConfigKey

logic_packets = []

def cb(dev: Device, packet: Packet):
    print(f"{dev.model} recorded {packet}")
    if isinstance(packet, LogicPacket):
        logic_packets.append(packet)
    return len(logic_packets) < 10  # return False to stop acquisition


with (
    Sigrok() as sr,
    sr.get_driver("demo") as driver,
    driver.get_device() as device
):
    device.set_config_uint64(ConfigKey.SR_CONF_SAMPLERATE, 1000)
    device.enable_channels("D0")
    sr.run(cb, [device])
```
