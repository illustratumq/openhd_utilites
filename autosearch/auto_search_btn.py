import RPi.GPIO as GPIO
import datetime
import socket
import logging
import time

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(message)s")

tcp_HOST = "0.0.0.0"
tcp_PORT = 7891
BUTTON_PIN = 18
GPIO.setmode(GPIO.BCM)  
GPIO.setwarnings(False)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
previous_btn_status = GPIO.input(BUTTON_PIN)
start_time = datetime.datetime.now()
debug = False

def main(tcp_host: str, tcp_port: int, previous_btn_status: bool, current_btn_status: bool, start_time: datetime.datetime, debug: bool = False):
    logging.info(
        f"Start button monitor with button status: {previous_btn_status}"
    )
    btn_pushed_time = 0
    while True:
        current_btn_status = GPIO.input(BUTTON_PIN)
        if previous_btn_status == 0 and current_btn_status == 1:
            if (datetime.datetime.now() - start_time).seconds >= 5:
                logging.info(f"Button pushed now, wait for holding 2 sec")
                if btn_pushed_time == 0:
                    btn_pushed_time = datetime.datetime.now()
        elif previous_btn_status == 1 and current_btn_status == 1 and btn_pushed_time != 0:
            if (datetime.datetime.now() - btn_pushed_time).seconds >= 2:
                    logging.info("Button pushed 2 sec")
                    with socket.create_connection((tcp_host, tcp_port), timeout=2) as sock:
                        message = "DO_AUTO_SEARCH:True\n".encode('utf-8')
                        logging.info("Send autosearch command")
                        sock.sendall(message)
                    start_time = datetime.datetime.now()
                    btn_pushed_time = 0
        elif previous_btn_status == 0 and current_btn_status == 0:
            btn_pushed_time = 0
        if debug:
            logging.info(f"current_btn_status={current_btn_status}, btn_pushed_time={btn_pushed_time}, previous_btn_status={previous_btn_status}")
        time.sleep(0.2)
        previous_btn_status = current_btn_status


main(tcp_HOST, tcp_PORT, previous_btn_status, previous_btn_status, start_time, debug)