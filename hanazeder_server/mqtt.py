import asyncio
from time import sleep

import argparse
import sys



from hanazeder_server.MqttClient import MqttClient

async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial-port", help="set serial port",
                    type=str)
    parser.add_argument("mqtt_server", help="MQTT server")
    parser.add_argument("--mqtt-port", help="MQTT server port", default=1883,
                    type=int)
    parser.add_argument("--mqtt-user", help="MQTT username", type=str)
    parser.add_argument("--mqtt-password", help="MQTT password", type=str, default=None)
    parser.add_argument("--home-assistant", help="Set Home Assistant auto-detect", action="store_true")
    parser.add_argument("--device-id", help="Device id, used for topic structure and to identify these devices within HA", default="hanazeder")
    parser.add_argument("--debug", help="print low-level messages", action="store_true")
    parser.add_argument("--address", help="connect to HOSTNAME RS232-adapter, needs port as well",
                    type=str)
    parser.add_argument("--port", help="connect to HOSTNAME on port PORT",
                    type=int, default=5000)
    args = parser.parse_args()

    if args.address and args.serial_port:
        print('Cannot specify both serial-port and address')
        return 1
    if not args.address and not args.serial_port:
        print('Specify either serial port or RS-232 converter hostname')
        return 1
    
    if args.address and not args.port:
        print('Specify port together with address')
        return 2
    if not args.mqtt_server:
        print('Need to specify MQTT server')
        return 3
    
    while True:
        try:
            mqtt_instance = MqttClient(args.device_id, args.mqtt_server, args.mqtt_user, args.mqtt_password, args.mqtt_port, args.debug)
            await mqtt_instance.connect(args.serial_port, args.address, args.port)
            await mqtt_instance.read_names_block()
            await mqtt_instance.conn.wait_for_empty_queue()
            await mqtt_instance.fetch_missing_names()
            await mqtt_instance.conn.wait_for_empty_queue()
            await mqtt_instance.publish_base()
            while True:
                await mqtt_instance.run_loop()
                await mqtt_instance.conn.wait_for_empty_queue()
                await asyncio.sleep(30)
        except Exception as e:
            try:
                mqtt_instance.connection.close()
            except Exception as e2:
                print(f'Cannot close connection', e2)
            print(f'Error while reading, will sleep and retry', e)
            await asyncio.sleep(90)

    


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))