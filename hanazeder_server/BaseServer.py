from typing import List
from hanazeder.Hanazeder import HanazederFP, SENSOR_LABELS, ConfigEntry
from hanazeder.comm import InvalidHeaderException, ChecksumNotMatchingException

class BaseServer:

    names: List[str] = []
    conn: HanazederFP = None

    def __init__(self, device_id, debug):
        self.device_id = device_id
        self.debug = debug
    
    async def on_info_read(self, dev):
        pass

    async def on_name_read(self, index: int, name: str):
        self.names[index] = name

    async def on_names_read(self, configs: List[ConfigEntry]):
        for index, config_label in enumerate(configs):
            self.names.append(None)
            if config_label.value > 0 and config_label.value < len(SENSOR_LABELS):
                self.names[index] = SENSOR_LABELS[config_label.value]
    
    async def connect(self, serial_port: str = None, address: str = None, port: int = 3000):
        while True:
            try:
                self.conn = HanazederFP(debug=self.debug)
                await self.conn.open(serial_port=serial_port, address=address, port=port, timeout=2)
                await self.conn.read_information(self.on_info_read)
                # We need to wait for this so we know type and version
                await self.conn.wait_for_empty_queue()
                print(f'Connected to {self.conn.device_type.name} with version {self.conn.version}')
                break
            except (InvalidHeaderException, ChecksumNotMatchingException) as e:
                print('Cannot read info, retrying', e)
    
    async def read_names_block(self):
        # Read label from fixed list
        names = []
        await self.conn.read_config_block(27, 15, self.on_names_read)
    
    async def fetch_missing_names(self):
        for index, name in enumerate(self.names):
            if name == None:
                await self.conn.read_sensor_name(index, self.on_name_read)