from asyncio_mqtt import Client, ProtocolVersion, Will
from copy import copy
import json

from .BaseServer import BaseServer


class MqttClient(BaseServer):
    def __init__(
                    self,
                    device_id,
                    mqtt_server,
                    mqtt_user=None,
                    mqtt_password=None,
                    mqtt_port: int = 1883,
                    debug=False):
        super(MqttClient, self).__init__(device_id, debug)
        self.base_topic = f'hanazeder/{device_id}'

        will = Will(f'{self.base_topic}/state', payload='offline', retain=True)

        self.mqttc = Client(
                    mqtt_server,
                    port=mqtt_port,
                    will=will,
                    client_id="hanazeder",
                    clean_session=True,
                    protocol=ProtocolVersion.V311,
                    transport="tcp",
                    username=mqtt_user,
                    password=mqtt_password)
    
    async def connect(
                    self,
                    serial_port: str = None,
                    address: str = None,
                    port: int = 3000):
        await super(MqttClient, self).connect(serial_port, address, port)
        connections = []
        if serial_port:
            connections.append(['serial', serial_port])
        else:
            connections.append(['ip', f'{address}:{port}'])
        # HA base config topic
        self.ha_base_config = {
            'availability': [{'topic': f'{self.base_topic}/state'}],
            'device': {
                'manufacturer': "Hanazeder",
                'connections': connections,
                'identifiers': [self.device_id],
                'name': self.conn.device_type.name,
                'model': self.conn.device_type.name,
                'sw_version': self.conn.version,
            },
            'enabled_by_default': True
        }
        await self.mqttc.connect()

        await self.mqttc.publish(
            f'{self.base_topic}/state', 'online',
            retain=True)
    
    async def publish_base(self):
        for sensor_idx, name in enumerate(self.names):
            print(f'Sensor {sensor_idx} has name {name}')
            unique_id = f'{self.device_id}-f{sensor_idx}'
            ha_config = copy(self.ha_base_config)
            ha_config['device_class'] = 'temperature'
            ha_config['state_class'] = 'measurement'
            ha_config['name'] = name
            ha_config['unit_of_measurement'] = '°C'
            ha_config['unique_id'] = unique_id
            ha_config['state_topic'] = f'{self.base_topic}/sensor/{sensor_idx}'
            ha_config['value_template'] = '{{ value_json.temperature }}'
            await self.mqttc.publish(
                f'homeassistant/sensor/{unique_id}/temperature/config',
                json.dumps(ha_config, ensure_ascii=False).encode('utf8'),
                retain=True)
            
        # Setup energy config
        ha_config = copy(self.ha_base_config)
        unique_id = f'{self.device_id}-power'
        ha_config['device_class'] = 'power'
        ha_config['state_class'] = 'measurement'
        ha_config['name'] = f'{self.device_id} Power'
        ha_config['unit_of_measurement'] = 'kW'
        ha_config['unique_id'] = unique_id
        ha_config['state_topic'] = f'{self.base_topic}/power'
        await self.mqttc.publish(
            f'homeassistant/sensor/{unique_id}/power/config',
            json.dumps(ha_config, ensure_ascii=False).encode('utf8'),
            retain=True)

        ha_config = copy(self.ha_base_config)
        unique_id = f'{self.device_id}-energy'
        ha_config['device_class'] = 'energy'
        ha_config['state_class'] = 'total'
        ha_config['name'] = f'{self.device_id} Energy'
        ha_config['unit_of_measurement'] = 'kWh'
        ha_config['unique_id'] = unique_id
        ha_config['state_topic'] = f'{self.base_topic}/energy'
        await self.mqttc.publish(
            f'homeassistant/sensor/{unique_id}/energy/config',
            json.dumps(ha_config, ensure_ascii=False).encode('utf8'),
            retain=True)

        ha_config = copy(self.ha_base_config)
        unique_id = f'{self.device_id}-impulse'
        ha_config['device_class'] = 'frequency'
        ha_config['state_class'] = 'measurement'
        ha_config['name'] = f'{self.device_id} Impulses'
        ha_config['unit_of_measurement'] = 'Hz'
        ha_config['unique_id'] = unique_id
        ha_config['state_topic'] = f'{self.base_topic}/impulse'
        await self.mqttc.publish(
            f'homeassistant/sensor/{unique_id}/impulse/config',
            json.dumps(ha_config, ensure_ascii=False).encode('utf8'),
            retain=True)
    
    async def run_loop(self):
        # Read all sensor values
        for sensor_idx in range(0, 15):
            # Skip unconnected sensors
            if self.names[sensor_idx] is None:
                continue
            if self.debug:
                print(f'Reading sensor {sensor_idx}')
            value = await self.conn.read_sensor(sensor_idx)
            await self.mqttc.publish(
                f'{self.base_topic}/sensor/{sensor_idx}',
                json.dumps({'temperature': value}))
                
        energy = await self.conn.read_energy()
        # TODO: parallelize
        await self.mqttc.publish(f'{self.base_topic}/energy', energy[0])
        await self.mqttc.publish(f'{self.base_topic}/power', energy[1])
        await self.mqttc.publish(f'{self.base_topic}/impulse', energy[2])
        if self.debug:
            print('Energy readings:')
            print(f'  Total   {energy[0]}')
            print(f'  Current {energy[1]}')
            print(f'  Impulse {energy[2]}')
