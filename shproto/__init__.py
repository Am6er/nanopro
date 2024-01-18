from struct import unpack

import shproto.port

SHPROTO_START = 0xFE  # 254
SHPROTO_ESC = 0xFD  # 253
SHPROTO_FINISH = 0xA5  # 165
BUFFER_SIZE = 8192
MODE_HISTOGRAM = 0x01
MODE_PULSE = 0x02
MODE_TEXT = 0x03
MODE_STAT = 0x04
MODE_BOOTLOADER = 0xF3  # 243

INITIAL_MODBUS = 0xFFFF
INITIAL_DF1 = 0x0000

crc16table = (
0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040 )

#def init_table( ):
#    # Initialize the CRC-16 table,
#    #   build a 256-entry list, then convert to read-only tuple
#    global table
#
#    1st = []
#    for i in range(256):
#        data = i << 1
#        crc = 0
#        for j in range(8, 0, -1):
#            data >>= 1
#            if (data ^ crc) & 0x0001:
#                crc = (crc >> 1) ^ 0xA001
#            else:
#                crc >>= 1
#
#        1st.append( crc)
#
#    table = tuple( lst)
#    return 



def crc16(crc, ch):
    """Given a new Byte and previous CRC, Calc a new CRC-16"""
#    if type(ch) == type("c"):
#        by = ord( ch)
#    else:
#        by = ch
#    crc = (crc >> 8) ^ crc16table[(crc ^ by) & 0xFF]
    crc = (crc >> 8) ^ crc16table[(crc ^ ch) & 0xFF]
    return (crc & 0xFFFF)

def crc16bytes(crc, st):
    """Given a bunary string and starting CRC, Calc a final CRC-16 """
    for ch in st:
        #crc = (crc >> 8) ^ crc16table[(crc ^ ord(ch)) & 0xFF]
        crc = (crc >> 8) ^ crc16table[(crc ^ ch) & 0xFF]
    return crc



def crc16_old(crc, data):
    crc ^= data
    for _ in range(8):
        if (crc & 0x0001) != 0:
            crc = ((crc >> 1) ^ 0xA001)
        else:
            crc = (crc >> 1)
    return crc


class packet:
    payload = []
    raw_data = []
    crc = 0xFFFF
    cmd = 0x00
    ready = 0
    len = 0
    esc = 0
    dropped = 0

    def clear(self):
        self.payload = []
        self.crc = 0xFFFF
        self.ready = 0
        self.len = 0
        self.esc = 0
        self.dropped = 0

    def add(self, tx_byte):
        if self.len >= BUFFER_SIZE:
            return
        self.crc = crc16(self.crc, tx_byte)
        if tx_byte == SHPROTO_START or tx_byte == SHPROTO_FINISH or tx_byte == SHPROTO_ESC:
            self.payload.append(SHPROTO_ESC)
            self.payload.append((~tx_byte) & 0xFF)
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
        if self.len >= BUFFER_SIZE:
            return 0
        self.payload.append(SHPROTO_FINISH)
        self.len = len(self.payload)
        return self.len

    def read(self, rx_byte):
        self.raw_data.append(rx_byte)
        # rx_byte = unpack("<B", rx_byte)[0]
        if rx_byte == SHPROTO_START:
            self.clear()
            return
        if rx_byte == SHPROTO_ESC:
            self.esc = 1
            return
        if rx_byte == SHPROTO_FINISH:
            self.crc = crc16bytes(self.crc, [self.cmd] + self.payload)
            self.len -= 3  # minus command (1 byte) and crc16 (2 bytes)
            if not self.crc:
                self.ready = 1
            else:
                self.dropped = 1
                inf_str = ''
                if self.len > 2:
                    inf_str = " H offset: {}".format(self.payload[0] & 0xFF | ((self.payload[1] & 0xFF) << 8))
                # print("Dropped cmd {} len {} crc {:04x}{}"
                #     .format(self.cmd, self.len, self.crc, inf_str))
                # print("Dropped cmd {} len {} crc {}\n raw data: {}\n payload: {}\n\n"
                #      .format(self.cmd, self.len, self.crc, self.raw_data, self.payload))
            self.raw_data = []
            return
        if self.esc:
            self.esc = 0
            rx_byte = (~rx_byte) & 0xFF
        if self.len:
            self.payload.append(rx_byte)
        else:
            self.cmd = rx_byte
        if self.len < BUFFER_SIZE:
            self.len += 1
            #self.crc = crc16(self.crc, rx_byte)
