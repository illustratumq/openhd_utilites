import datetime
import serial
import json
import logging
import socket
import sys

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(message)s")

class CRSF_FRAMETYPE:
    RC_CHANNELS_PACKED = 0x16
    RC_CHANNELS_LEN = 0x18
    CRSF_TX_SYNC_BYTE = 0xEE

def unpack_channels(payload: bytes) -> list[int]:
    """
    Посилання на формат: https://github.com/crsf-wg/crsf/wiki/CRSF_FRAMETYPE_RC_CHANNELS_PACKED
    """
    num_channels = 16
    src_bits = 11
    input_channel_mask = (1 << src_bits) - 1

    channels = []
    read_value = 0
    bits_merged = 0
    byte_index = 0

    for _ in range(num_channels):
        while bits_merged < src_bits:
            if byte_index >= len(payload):
                raise ValueError("Payload is too short to unpack all channels.")
            read_value |= payload[byte_index] << bits_merged
            bits_merged += 8
            byte_index += 1

        channel_value = read_value & input_channel_mask
        channels.append(channel_value)

        read_value >>= src_bits
        bits_merged -= src_bits

    return channels

def get_rc_channel(channels: list[int], channel_number: int) -> int:
    crsf_value = channels[channel_number - 1]
    if crsf_value <= 992:
        return int(988 + 0.625 * (crsf_value - 172))
    else:
        return int(1500 + 0.625 * (crsf_value - 992))


def crc8_dvb_s2(crc, data):
    poly = 0xD5
    crc ^= data
    for _ in range(8):
        if crc & 0x80:
            crc = ((crc << 1) ^ poly) & 0xFF
        else:
            crc = (crc << 1) & 0xFF
    return crc

def crsf_validate_frame(frame: bytes) -> bool:
    data = frame[2:-1]
    crc = 0
    for byte in data:
        crc = crc8_dvb_s2(crc, byte)
    return crc == frame[-1]

def read_crsf_packet(ser: serial.Serial, debug_mode: bool) -> bytes:
    while True:
        byte = ser.read(1)
        if not byte:
            continue
        if byte[0] != CRSF_FRAMETYPE.CRSF_TX_SYNC_BYTE:
            continue

        length = ser.read(1)
        if not length or length[0] != CRSF_FRAMETYPE.RC_CHANNELS_LEN:
            continue

        frame_type = ser.read(1)
        if not frame_type or frame_type[0] != CRSF_FRAMETYPE.RC_CHANNELS_PACKED:
            continue

        rest = ser.read(CRSF_FRAMETYPE.RC_CHANNELS_LEN - 1)  # Already read 1 from length
        if len(rest) != CRSF_FRAMETYPE.RC_CHANNELS_LEN - 1:
            continue

        packet = byte + length + frame_type + rest

        if crsf_validate_frame(packet):
            if debug_mode:
                logging.info(f"[VALID]: {' '.join(map(lambda b: hex(b), packet))}")
            return packet
        else:
            if debug_mode:
                logging.info(f"[CRC_FAIL]: {' '.join(map(lambda b: hex(b), packet))}")

def main(uart_port: str, baud_rate: int, tcp_host: str, tcp_port: str, timeout: int, debug_mode: bool):
    now = datetime.datetime.now()
    try:
        ser = serial.Serial(uart_port, baud_rate, timeout=timeout)
        if debug_mode:
            logging.info(f"[serial]: connected to UART port {uart_port} at {baud_rate} baud.")
    except Exception as e:
        logging.info(f"[serial]: failed to open UART port: {e}")
        return 0

    try:
        with open("/home/openhd/openhd_custom_params.json", mode="r", encoding="utf-8") as fp:
            channels = json.load(fp)["channels"]
            channels_count = len(channels)
        while True:
            packet = read_crsf_packet(ser, debug_mode)
            channels = unpack_channels(packet[3:-1])
            rc_channel = get_rc_channel(channels, 10)
            if datetime.datetime.now() - now > datetime.timedelta(seconds=1):
                with socket.create_connection((tcp_host, tcp_port), timeout=2) as sock:
                    freq_index = int((rc_channel - 988) / (1024 / channels_count))
                    message = f"FREQ_INDEX:{freq_index}\n".encode('utf-8')
                    logging.info(f"Sending message: {message} | RC: {rc_channel}")
                    sock.sendall(message)
                now = datetime.datetime.now()
            # тут можна додати відправку через tcp або іншу обробку
    except KeyboardInterrupt:
        logging.info("Terminating...")
    except Exception as e:
        logging.info(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    tcp_HOST = "0.0.0.0"
    tcp_PORT = 7890
    SERIAL_TIMEOUT = 8
    SERIAL_BAUDRATE = 420000
    SERIAL_PORT = '/dev/serial0'
    DEBUG_MODE = False

    logging.info("Run script")
    main(SERIAL_PORT, SERIAL_BAUDRATE, tcp_HOST, tcp_PORT, SERIAL_TIMEOUT, DEBUG_MODE)
