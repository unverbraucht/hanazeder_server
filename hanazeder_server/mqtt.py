import asyncio
import argparse
import sys
import logging

from quart import Quart

from hanazeder_server.BaseServer import BaseServer
from hanazeder_server.MqttClient import MqttClient

logging.basicConfig(format='%(asctime)s %(message)s')

parser = argparse.ArgumentParser()
parser.add_argument("--serial-port", help="set serial port",
                    type=str)
parser.add_argument("--mqtt-server", help="MQTT server")
parser.add_argument("--mqtt-port", help="MQTT server port", default=1883,
                    type=int)
parser.add_argument("--mqtt-user", help="MQTT username", type=str)
parser.add_argument("--mqtt-password", help="MQTT password", type=str,
                    default=None)
parser.add_argument(
    "--home-assistant",
    help="Set Home Assistant auto-detect",
    action="store_true")
parser.add_argument(
    "--device-id",
    help="Device id, used for topic structure and to identify within HA",
    default="hanazeder")
parser.add_argument("--debug", help="print low-level messages", action="store_true")
parser.add_argument(
    "--address",
    help="connect to HOSTNAME RS232-adapter, needs port as well",
    type=str)
parser.add_argument(
    "--port",
    help="connect to HOSTNAME on port PORT",
    type=int, default=5000)
args = parser.parse_args()

if args.address and args.serial_port:
    print('Cannot specify both serial-port and address')
    sys.exit(1)
if not args.address and not args.serial_port:
    print('Specify either serial port or RS-232 converter hostname')
    sys.exit(1)

if args.address and not args.port:
    print('Specify port together with address')
    sys.exit(2)

if args.debug:
    logging.basicConfig(level=logging.DEBUG)

app = Quart(__name__)


def create_instance():
    if args.mqtt_server:
        return MqttClient(
                    args.device_id,
                    args.mqtt_server,
                    args.mqtt_user,
                    args.mqtt_password,
                    args.mqtt_port,
                    args.debug)
    else:
        return BaseServer(args.device_id, args.debug)


async def mqtt_loop():
    while not hasattr(app, 'mqtt_instance') or app.mqtt_instance.running:
        try:
            app.mqtt_instance = create_instance()
            await app.mqtt_instance.connect(
                args.serial_port,
                args.address,
                args.port)
            await app.mqtt_instance.read_names_block()
            await app.mqtt_instance.publish_base()
            while app.mqtt_instance.running:
                await app.mqtt_instance.run_loop()
                if not app.mqtt_instance.conn.connected:
                    break
                await asyncio.sleep(30)
        except Exception as e:
            try:
                app.mqtt_instance.close()
            except Exception as e2:
                print('Cannot close connection', e2)
            print('Error while reading, will sleep and retry', e)
            if app.mqtt_instance.running:
                await asyncio.sleep(90)


@app.before_serving
async def startup():
    asyncio.get_event_loop().create_task(mqtt_loop())


@app.after_serving
async def shutdown():
    app.mqtt_instance.shutdown()
    app.mqtt_instance.close()


@app.get("/api/data")
async def echo():
    if app.mqtt_instance:
        return app.mqtt_instance.as_dict()
    return {
        "running": False
    }

app.run()
