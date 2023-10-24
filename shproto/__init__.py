import shproto.port

SHPROTO_START = (0xFE | 0x80)
SHPROTO_ESC = (0xFD | 0x80)
SHPROTO_FINISH = (0xA5 | 0x80)
MODE_HISTOGRAM = 0x01
MODE_OSCILO = 0x02
MODE_TEXT = 0x03
MODE_STAT = 0x04
MODE_BOOTLOADER = 0xF3


def crc16(crc: int, data: bytes):
    crc ^= int(data)
    for _ in range(8):
        if (crc & 0x0001) != 0:
            crc = ((crc >> 1) ^ 0xA001)
        else:
            crc = (crc >> 1)
    return crc


class packet:
    payload = []
    crc = 0xFFFF
    cmd = 0x00
    ready = 0
    len = 0
    esc = 0
    buffer_size = 4096
    dropped = 0

    def clear(self):
        self.payload = []
        self.crc = 0xFFFF
        self.cmd = 0x00
        self.ready = 0
        self.len = 0
        self.esc = 0
        self.buffer_size = 4096
        self.dropped = 0

    def add(self, tx_byte):
        if self.len >= self.buffer_size:
            return
        self.crc = crc16(self.crc, tx_byte)
        if tx_byte == SHPROTO_START or tx_byte == SHPROTO_FINISH or tx_byte == SHPROTO_ESC:
            self.payload.append(SHPROTO_ESC)
            self.payload.append(tx_byte & 0xFF)
            self.len = len(self.payload)
        else:
            self.payload.append(tx_byte)
            self.len += 1

    def start(self):
        self.len = 0
        self.crc = 0xFFFF
        self.payload = [0xFF, SHPROTO_START]
        self.len = len(self.payload)
        self.add(self.cmd)

    def stop(self):
        _crc = self.crc
        self.add(_crc & 0xFF)
        self.add(_crc >> 8)
        if self.len >= self.buffer_size:
            return 0
        self.payload.append(SHPROTO_FINISH)
        self.len = len(self.payload)
        return self.len

    def read(self, rx_byte):
        if rx_byte == SHPROTO_START:
            self.clear()
            return
        if rx_byte == SHPROTO_ESC:
            self.esc = 1
            return
        if rx_byte == SHPROTO_FINISH:
            if not self.crc:
                self.len -= 3  # minus command (1 byte) and crc16 (2 bytes)
                self.ready = 1
                return
            else:
                self.dropped = 1
        if self.esc:
            self.esc = 0
            rx_byte = ~rx_byte
        if self.len < self.buffer_size:
            if self.len > 0:
                self.payload.append(rx_byte)
            else:
                self.cmd = rx_byte
            self.len += 1
            self.crc = crc16(self.crc, rx_byte)
