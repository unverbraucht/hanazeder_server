This server connects to a heating pump control system made by the company Hanazeder.

# Requirements

The server runs on Linux, OSX and Windows and needs Python >= 3.6

## Hardware requirements
- Supported Hanazeder system (see next paragraph)
- Linux, OSX or Windows system
  - A Raspberry Pi (even a Zero or 1st gen) works fine
- A serial (RS232) connection to the pump. This can take one of two forms
  - The system is directly connected to the Hanazeder board, typically through a RS232 to USB adapter. Please note that I needed a nullmodem cable to get data to flow, so if nothing can be read buy a RS232 null-modem cable and plug between device and pump controller.
  - A RS232-to-TCP converter [something like this](https://cablematic.com/de/products/category/server-tcpip-rs232/)

## Supported Hanazeder systems
Supported systems are
- Hanazeder FP1 (untested)
- Hanazeder FP2 (untested)
- Hanazeder FP3 (untested)
- Hanazeder FP6 (untested)
- Hanazeder FP10
- Hanazeder SH series might also work, please test and let me know!

As you can see quite a few of the systems are untested. Since we do not write anything
into the pumps I don't expect any issues.

# Installation
Install from pip:
```
pip install hanazeder_server
```


# Starting
A simple example of reading from a USB-to-RS232 adapter (`/dev/ttyUSB0`) and posting the data to the MQTT broker at `192.168.1.1` is
```
python -m hanazeder_server.mqtt --serial-port/dev/ttyUSB0  192.168.1.1
```

A more complex example will read from a RS232-to-TCP converter at 192.168.1.2 port 3000 and post the data to the MQTT broker at 192.168.1.1, using the username MQTT-USER and password MQTT-PASSWORD to log into the broker. It will print debug information to stdout.
```
python -m hanazeder_server.mqtt --address 192.168.1.2 --port 3000  --mqtt-user MQTT-USER --mqtt-password MQTT-PASSWORD --debug 192.168.1.1
```

