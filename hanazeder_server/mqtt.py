import json
from time import sleep
from hanazeder.Hanazeder import HanazederFP, SENSOR_LABELS
from hanazeder.comm import InvalidHeaderException, ChecksumNotMatchingException
import argparse
import sys
import paho.mqtt.client as mqtt
from copy import copy

def main() -> int:
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
    
    base_topic = f'hanazeder/{args.device_id}'

    mqttc = mqtt.Client(client_id="hanazeder", clean_session=True, userdata=None, protocol=mqtt.MQTTv311, transport="tcp")
    if args.mqtt_user:
        mqttc.username_pw_set(args.mqtt_user, args.mqtt_password)
    mqttc.connect(args.mqtt_server, args.mqtt_port, 60)
    mqttc.will_set(f'{base_topic}/state', payload="offline", qos=1, retain=True)
    mqttc.publish(f'{base_topic}/state', 'online', retain=True)
    try:
        conn = None
        while True:
            try:
                conn = HanazederFP(serial_port=args.serial_port, address=args.address, port=args.port, debug=args.debug)
                conn.read_information()
                print(f'Connected to {conn.device_type.name} with version {conn.version}')
                break
            except (InvalidHeaderException, ChecksumNotMatchingException) as e:
                print('Cannot read info, retrying', e)

        connections = []
        if args.serial_port:
            connections.append(['serial', args.serial_port])
        else:
            connections.append(['ip', f'{args.address}:{args.port}'])
        # HA base config topic
        ha_base_config = {
            'availability': [{'topic':f'{base_topic}/state'}],
            'device': {
                'manufacturer': "Hanazeder",
                'connections': connections,
                'identifiers': [args.device_id],
                'name': conn.device_type.name,
                'model': conn.device_type.name,
                'sw_version': conn.version,
            },
            'enabled_by_default': True
        }

        # Read label from fixed list
        names = []
        configs = conn.read_config_block(27, 15)
        sensor_idx = 0
        for config_label in configs:
            if config_label.value > 0:
                name = SENSOR_LABELS[config_label.value]
            else:
                # Read label from device
                name = conn.read_sensor_name(sensor_idx)
            print(f'Sensor {sensor_idx} has name {name}')
            unique_id = f'{args.device_id}-f{sensor_idx}'
            ha_config = copy(ha_base_config)
            ha_config['device_class'] = 'temperature'
            ha_config['state_class'] = 'measurement'
            ha_config['name'] = name
            ha_config['unit_of_measurement'] = '°C'
            ha_config['unique_id'] = unique_id
            ha_config['state_topic'] = f'{base_topic}/sensor/{sensor_idx}'
            ha_config['value_template'] = '{{ value_json.temperature }}'
            mqttc.publish(f'homeassistant/sensor/{unique_id}/temperature/config', json.dumps(ha_config, ensure_ascii=False).encode('utf8'), retain=True)
            names.append(name)
            sensor_idx = sensor_idx + 1
        
        # Setup energy config
        ha_config = copy(ha_base_config)
        unique_id = f'{args.device_id}-power'
        ha_config['device_class'] = 'power'
        ha_config['state_class'] = 'measurement'
        ha_config['name'] = f'{args.device_id} Power'
        ha_config['unit_of_measurement'] = 'kW'
        ha_config['unique_id'] = unique_id
        ha_config['state_topic'] = f'{base_topic}/power'
        mqttc.publish(f'homeassistant/sensor/{unique_id}/power/config', json.dumps(ha_config, ensure_ascii=False).encode('utf8'), retain=True)

        ha_config = copy(ha_base_config)
        unique_id = f'{args.device_id}-energy'
        ha_config['device_class'] = 'energy'
        ha_config['state_class'] = 'total'
        ha_config['name'] = f'{args.device_id} Energy'
        ha_config['unit_of_measurement'] = 'kWh'
        ha_config['unique_id'] = unique_id
        ha_config['state_topic'] = f'{base_topic}/energy'
        mqttc.publish(f'homeassistant/sensor/{unique_id}/energy/config', json.dumps(ha_config, ensure_ascii=False).encode('utf8'), retain=True)

        ha_config = copy(ha_base_config)
        unique_id = f'{args.device_id}-impulse'
        ha_config['device_class'] = 'frequency'
        ha_config['state_class'] = 'measurement'
        ha_config['name'] = f'{args.device_id} Impulses'
        ha_config['unit_of_measurement'] = 'Hz'
        ha_config['unique_id'] = unique_id
        ha_config['state_topic'] = f'{base_topic}/impulse'
        mqttc.publish(f'homeassistant/sensor/{unique_id}/impulse/config', json.dumps(ha_config, ensure_ascii=False).encode('utf8'), retain=True)
            
        # mqttc.publish(f'{base_topic}/energy/total/type', 'energy')
        # mqttc.publish(f'{base_topic}/energy/current/type', 'power')
        # mqttc.publish(f'{base_topic}/energy/impulse/type', 'frequency')
        # mqttc.publish(f'{base_topic}/energy/total/state', 'total')
        # mqttc.publish(f'{base_topic}/energy/current/state', 'measurement')
        # mqttc.publish(f'{base_topic}/energy/impulse/state', 'measurement')
        # mqttc.publish(f'{base_topic}/energy/total/unit_of_measurement', 'kWh')
        # mqttc.publish(f'{base_topic}/energy/current/unit_of_measurement', 'W')
        
        while True:
            mqttc.loop(timeout=2)
            # Read all sensor labels
            for sensor_idx in range(0, 15):
                mqttc.loop(timeout=0.1)
                if args.debug:
                    print(f'Reading sensor {sensor_idx}')
                try:
                    value = conn.read_sensor(sensor_idx)
                except (InvalidHeaderException, ChecksumNotMatchingException)  as e:
                    print(f'Cannot read sensors', e)
                    sleep(3)
                if args.debug:
                    print(f'Sensor value is {value}')
                if value:
                    mqttc.publish(f'{base_topic}/sensor/{sensor_idx}', json.dumps({'temperature': value}))
            try:
                energy = conn.read_energy()
                mqttc.publish(f'{base_topic}/energy', energy[0], retain=True)
                mqttc.publish(f'{base_topic}/power', energy[1], retain=True)
                mqttc.publish(f'{base_topic}/impulse', energy[2], retain=True)
                if args.debug:
                    print('Energy readings:')
                    print(f'  Total   {energy[0]}')
                    print(f'  Current {energy[1]}')
                    print(f'  Impulse {energy[2]}')
            except (InvalidHeaderException, ChecksumNotMatchingException) as e:
                print('Cannot read energy', e)
            sleep(2)
    finally:    
        if mqttc:
            mqttc.publish(f'{base_topic}/state', 'offline', retain=True)


    return 0

if __name__ == '__main__':
    sys.exit(main())