from typing import List
from hanazeder.Hanazeder import HanazederFP, SENSOR_LABELS
from hanazeder.comm import InvalidHeaderException, ChecksumNotMatchingException


class BaseServer:
    running = True
    names: List[str] = []
    conn: HanazederFP = None
    sensor_value = [None] * 16
    energy = [None] * 3

    def __init__(self, device_id, debug):
        self.device_id = device_id
        self.debug = debug

    async def connect(
                    self,
                    serial_port: str = None,
                    address: str = None,
                    port: int = 3000):
        while True:
            try:
                self.conn = HanazederFP(debug=self.debug)
                await self.conn.open(
                    serial_port=serial_port,
                    address=address,
                    port=port,
                    timeout=2)
                await self.conn.read_information()
                print(f'Connected to {self.conn.device_type.name} with version {self.conn.version}')
                break
            except (InvalidHeaderException, ChecksumNotMatchingException) as e:
                print('Cannot read info, retrying', e)

    async def read_names_block(self):
        # Read label from fixed list
        configs = await self.conn.read_config_block(27, 15)
        for index, config_label in enumerate(configs):
            self.names.append(None)
            if config_label.value > 0 and \
                    config_label.value < len(SENSOR_LABELS):
                self.names[index] = SENSOR_LABELS[config_label.value]
            else:
                self.names[index] = await self.conn.read_sensor_name(index)

    async def publish_base(self):
        pass

    async def run_loop(self):
        # Read all sensor values
        for sensor_idx in range(0, 15):
            # Skip unconnected sensors
            if self.names[sensor_idx] is None:
                continue
            if self.debug:
                print(f'Reading sensor {sensor_idx}')
            self.sensor_value[sensor_idx] = \
                await self.conn.read_sensor(sensor_idx)

        self.energy = await self.conn.read_energy()
        if self.debug:
            print('Energy readings:')
            print(f'  Total   {self.energy[0]}')
            print(f'  Current {self.energy[1]}')
            print(f'  Impulse {self.energy[2]}')

    def as_dict(self):
        sensors = []
        # Add all sensor values
        for sensor_idx in range(0, 15):
            # Skip unconnected sensors
            if self.names[sensor_idx] is None:
                continue
            sensors.append({
                    "name":self.names[sensor_idx],
                    "value": self.sensor_value[sensor_idx]
                })
        return {
            "sensors": sensors,
            "energy": self.energy[0],
            "power": self.energy[1],
            "impulses": self.energy[2],
            "running": True
        }

    def close(self):
        if self.conn and self.conn.connection:
            self.conn.connection.close()
