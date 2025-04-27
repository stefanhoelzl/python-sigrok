# python-sigrok

Python-API for [libsigrok](https://sigrok.org/wiki/Libsigrok)

## Installation
```bash
pip install sigrok
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
from sigrok import Sigrok, ConfigKey

with (
    Sigrok() as sr,
    sr.get_driver("demo") as driver,
    driver.get_device() as device,
):
    device.set_config_uint64(ConfigKey.SR_CONF_SAMPLERATE, 1_000)
    device.set_config_uint64(ConfigKey.SR_CONF_LIMIT_SAMPLES, 10)
    device.enable_channels("D0")

    with sr.session(devices=[device]) as session:
        print(session.next_packet(timeout=1.0))
        print(session.next_packet(timeout=1.0))
        print(session.next_packet(timeout=1.0))
```
