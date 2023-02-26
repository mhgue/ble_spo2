#!/usr/bin/env python3
# Read Pulox Checkme O2
#
# see https://doc.qt.io/qtforpython/examples/example_async__minimal.html
#

import BLE_GATT
import gi
import json
import argparse
import copy
import os
import sys
import signal
import time

class ble_center(BLE_GATT.Central):
    '''
    BLE center with some extra methods
    '''
    def __init__(self, address):
        BLE_GATT.Central.__init__(self,address)
        signal.signal(signal.SIGTERM, self.signal_hdl)

    def signal_hdl(self, signum, frame):
        print("Signal:", signum, frame)
        self.mainloop.quit()

    # Convert a uuid to full size if needed
    def uuid(self,u):
        if isinstance(u,int):
            return self.uuid(f'{u:04X}')
        # For all BLE devices the 16 bit UUIDs are just a short for
        elif isinstance(u,str) and len(u) == 4:
            return f'0000{u}-0000-1000-8000-00805F9B34FB'
        return u

    def wait_for_notifications(self):
        """
        Has the effect of block the code from exiting. In the background it
        starts an event loop to listen for updates from the device
        """
        try:
            self.mainloop.run()
        except KeyboardInterrupt as e:
            self.cleanup()
            raise(e)

class pulox:
    '''
    Create a BLE device in central role and communicate with SpO2 sensor.
    '''
    rx = '0734594a-a8e7-4b1a-a6b1-cd5243059a57'
    tx = '8b00ace7-eb0b-49b0-bbe9-9aee0a26e1a3'
    rx_buf = bytearray()
    verbose = 0
    last_payload = None
    is_connected = False

    def __init__(self, mac):
        self.set_verbose()
        self.set_log_file_name()
        self.info_requested = False
        self.ble_address = mac
        self.ble = ble_center(self.ble_address)
        self.payload_time = time.time()

    def connect(self):
        self.is_connected = False
        try:
            self.ble.connect()
        except gi.repository.GLib.GError as e:
            if e.matches(gi.repository.Gio.io_error_quark(), gi.repository.Gio.IOErrorEnum.DBUS_ERROR):
                return False
            else:
                print(f'Connect failed: {e}')
                sys.exit(1)
        self.is_connected = True
        # Listen for RX data
        self.ble.on_value_change(self.rx, self.rx_notify)
        return self.is_connected

    def disconnect(self):
        self.ble.disconnect()

    # remove all notifications, exit the event loop, and disconnect from the peripheral device
    def cleanup(self):
        self.ble.cleanup()
        if (self.log_file):
            self.log_file.close()
            self.log_file = None

    def print_manufact(self):
        # Read manufacturer
        uuid = self.ble.uuid(0x2a29)
        self.manufact = bytes(self.ble.char_read(uuid)).decode('UTF-8')
        print(f"Manufacturer: {self.manufact}")

    def set_verbose(self, verbose=0):
        self.verbose = verbose

    def set_log_file_name(self, log_file_name = None):
        self.log_file_name = log_file_name
        self.log_file = None
        if (self.log_file_name):
            self.log_file = open(self.log_file_name,'w')
            print( 'Time; Epoch; SpO2; Puls; Batt; Count; Moves', file=self.log_file)

    def set_o2_low_action(self, cmd, limit):
        self.o2_low_action = cmd
        self.o2_low_action_limit = limit

    def set_o2_high_action(self, cmd, limit):
        self.o2_high_action = cmd
        self.o2_high_action_limit = limit

    def set_sensor_off_action(self, cmd):
        self.sensor_off_action = cmd

    def set_sensor_idle_action(self, cmd):
        self.sensor_idle_action = cmd

    def crc(self, bb):
        crc = 0x00
        for i in range(len(bb)):
            chk = (crc ^ bb[i]) & 0xFF
            crc = 0x00
            if ((chk & 0x01) > 0):
                crc ^= 0x07
            if ((chk & 0x02) > 0):
                crc ^= 0x0e
            if ((chk & 0x04) > 0):
                crc ^= 0x1c
            if ((chk & 0x08) > 0):
                crc ^= 0x38
            if ((chk & 0x10) > 0):
                crc ^= 0x70
            if ((chk & 0x20) > 0):
                crc ^= 0xe0
            if ((chk & 0x40) > 0):
                crc ^= 0xc7
            if ((chk & 0x80) > 0):
                crc ^= 0x89
        return crc

    def add_crc(self, bb):
        bb.append(self.crc(bb))

    # Create a command to transmitt
    def command(self, cmd, blk_id=0, payload=bytearray()):
        pkt = bytearray()
        pay_len = len(payload)
        pkt.append(0xaa)    # start of TX packet
        pkt.append(cmd)
        pkt.append(0xFF ^ cmd)
        pkt.append(blk_id & 0xFF)
        pkt.append(blk_id >> 8)
        pkt.append(pay_len & 0xFF)
        pkt.append(pay_len >> 8)
        pkt.extend(bytearray(payload))
        self.add_crc(pkt)
        return pkt

    # Send command
    def tx_cmd(self, cmd, blk_id=0, payload=bytearray()):
        if 1 < self.verbose:
            print(f'TX: cmd {cmd:02x}')
        pkt = self.command(cmd, blk_id, payload)
        self.ble.char_write(self.tx, pkt)

    def tx_request_io(self):
        self.tx_cmd(0x17)

    def tx_request_info(self):
        self.tx_cmd(0x14)
        self.info_requested = True

    def tx_file_open(self, filename):
        self.tx_cmd(0x03, 0, bytearray(filename).append(0))

    def tx_file_read(self, block):
        self.tx_cmd(0x04, block)

    def tx_file_close(self):
        self.tx_cmd(0x05)

    def do_action(self, cmd):
        if cmd:
            os.system(cmd)

    # Handle sensor readings from payload
    def rx_io_payload(self, payload):
        spo2 = payload[0]
        rpm = payload[1]
        flag = payload[2]  # 0xFF if sensor is off
        # Steps done in monitor mode
        step_cnt = payload[3] | (payload[4] << 8) | (
            payload[5] << 16) | (payload[6] << 24)
        batt = payload[7]
        rd1 = payload[8]
        moves = payload[9]
        str_spo2 = f' {spo2} % '
        str_rpm = f'{rpm} rpm'
        if flag == 0xFF:
            self.do_action(self.sensor_off_action)
            str_spo2 = str_rpm = '  off '
        elif flag == 0x00 and spo2 == 0x00 and rpm == 0x00:
            self.do_action(self.sensor_idle_action)
            str_spo2 = str_rpm = ' idle '
        else:
            if self.o2_low_action_limit and self.o2_low_action_limit >= spo2:
                self.do_action(self.o2_low_action)
            if self.o2_high_action_limit and self.o2_high_action_limit <= spo2:
                self.do_action(self.o2_high_action)
        ts=time.strftime('%H:%M:%S')
        ep=time.strftime('%s')
        if (0 < self.verbose):
            print(
                f'SpO2 {str_spo2}, Puls {str_rpm}, Batt {batt} %, Count {step_cnt}, Moves {moves}, ? {rd1}  ({payload.hex()})')
        else:
            print(
                f'{ts} SpO2 {str_spo2}, Puls {str_rpm}, Batt {batt} %, Count {step_cnt}, Moves {moves}')
        if (self.log_file):
            print( f'{ts}; {ep}; {str_spo2}; {str_rpm}; {batt}; {step_cnt}; {moves}', file=self.log_file )
            self.log_file.flush()
        return True

    def rx_json_payload(self, payload):
        try:
            # Device info reply is JSON with trailing zeros
            jstr = payload.decode('UTF-8').strip('\0')
            # print(f'RX: "{jstr}"')
        except:
            print(f'No string data: {payload.hex()}')
            return False
        try:
            self.json_info = json.loads(jstr)
        except:
            print(f'No JSON data: {jstr}')
            return False
        print(json.dumps(self.json_info, sort_keys=True, indent=4))
        self.info_requested = False
        return True

    def rx_payload(self, cmd, payload):
        pay_len = len(payload)
        if pay_len == 4:
            payvalue = payload[0] | (
                payload[1] << 8) | payload[2] << 16 | (payload[3] << 24)
            if (cmd == 0x01):
                if (payvalue == 0x0B):
                    print('Unknown command')
                elif (payvalue == 0x09):
                    print('File error')
                else:
                    print(f'unkonwn error 0x{payvalue:X}')
                return True
        if cmd == 0x00:
            if (payload != self.last_payload) or ((time.time() - self.payload_time) > 3):
                self.payload_time = time.time()
                self.last_payload = copy.deepcopy(payload)
                if pay_len == 0x0200:  # JSON device info
                    return self.rx_json_payload(payload)
                if pay_len == 0x0d:  # I/O sensor reading
                    return self.rx_io_payload(payload)
            else:
                return True
        return False

    def rx_pkt(self):
        while (len(self.rx_buf) > 0) and (self.rx_buf[0] != 0x55):
            self.rx_buf = self.rx_buf[1:]
        if len(self.rx_buf) < 8:
            return
        cmd = self.rx_buf[1]
        if (0xFF ^ cmd) != self.rx_buf[2]:
            print("rx cmd 0xff failed skipping")
            self.rx_buf = self.rx_buf[3:]
            self.rx_pkt()
            return  # Retry with skiped corrupted command
        if self.rx_buf[-1] != self.crc(self.rx_buf[:-1]):
            return  # CRC not valid (wait for more data)
        blk_id = self.rx_buf[3] | (self.rx_buf[4] << 8)
        if blk_id != 0x0000:
            print('RX block ID 0x%X' % blk_id)
            self.rx_buf = self.rx_buf[5:]
            self.rx_pkt()
            return  # Retry with skipped wrong block ID
        pay_len = self.rx_buf[5] | (self.rx_buf[6] << 8)
        if len(self.rx_buf) != (pay_len + 8):
            print('RX wrong packet len %d with payload %d' %
                  (len(self.rx_buf), pay_len))
            # Packet lost and request pending?
            if (self.info_requested):
                self.tx_request_info()
        if (pay_len > 0):
            payload = self.rx_buf[7:7+pay_len]
            self.rx_buf = bytearray()
            if self.rx_payload(cmd, payload):
                if (self.wait_for != 0):
                    self.tx_request_io()
                return
        print(f'Cmd:{cmd:X} Pay: {payload.hex()}')

    def rx_notify(self, value):
        if len(value) > 0:
            if (self.wait_for > 0):
                self.wait_for -= 1
            if (0 < self.verbose) and (0 < self.wait_for):
                print(f'Wait for {self.wait_for} events')
            self.rx_buf.extend(bytearray(value))
            self.rx_pkt()
            if (0 == self.wait_for):
                if 0 < self.verbose:
                    print(f'cleanup')
                self.cleanup()

    def wait_for_notifications(self, n=1):
        self.wait_for = n
        if (0 < self.verbose) and (0 < self.wait_for):
            print(f"Wait for {self.wait_for} events")
        if (self.wait_for != 0):

            self.ble.wait_for_notifications()


class cmd_line:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog='spo2.py',
            description='Communicate with Pulox Checkme 02 via BLE',
            epilog='Do enable BLE.'
        )
        self.parser.add_argument('MAC')
        self.parser.add_argument('-i', '--info', action='store_true')
        self.parser.add_argument('-m', '--manufact', action='store_true')
        self.parser.add_argument('-n', '--num_ev', action='store', default=-1, type=int,
                                 help='number of BLE events to wait for (-1 for ever)')
        self.parser.add_argument('-o', '--o2_min', action='store', default=90, type=int,
                                 help='SpO2 to take action if lower or equal')
        self.parser.add_argument('-O', '--o2_max', action='store', default=100, type=int,
                                 help='SpO2 to take action if higher or equal')
        self.parser.add_argument('-p', '--pulse_min', action='store', default=65, type=int,
                                 help='SpO2 to take action if lower or equal')
        self.parser.add_argument('-P', '--pulse_max', action='store', default=110, type=int,
                                 help='SpO2 to take action if higher or equal')
        self.parser.add_argument(
            '-e', '--sensor_idle_action', type=str, default=None, help='e.g. "spd-say -l EN "sensor idle" -i +100"')
        self.parser.add_argument(
            '-E', '--sensor_off_action', type=str, default=None)
        self.parser.add_argument(
            '-x', '--o2_low_action', type=str, default=None)
        self.parser.add_argument(
            '-X', '--o2_high_action', type=str, default=None)
        self.parser.add_argument(
            '-L', '--log', type=str, default=None)
        self.parser.add_argument('-v', '--verbose', action='count')
        self.args = self.parser.parse_args()

    def get_mac(self):
        return self.args.MAC

    def is_info(self):
        return self.args.info

    def do_gui(self):
        return self.args.gui

    def show_manufact(self):
        return self.args.manufact

    def get_num_events(self):
        return self.args.num_ev

    def get_verbose(self):
        return self.args.verbose

    def get_o2_low_action(self):
        return self.args.o2_low_action

    def get_o2_high_action(self):
        return self.args.o2_high_action

    def get_sensor_idle_action(self):
        return self.args.sensor_idle_action

    def get_sensor_off_action(self):
        return self.args.sensor_off_action

    def get_o2_min(self):
        return self.args.o2_min

    def get_o2_max(self):
        return self.args.o2_max

    def get_pulse_min(self):
        return self.args.pulse_min

    def get_pulse_max(self):
        return self.args.pulse_max

    def get_log_file_name(self):
        return self.args.log


if __name__ == '__main__':
    while True:
        try:
            cmd = cmd_line()
            # Connect to device with given MAC
            pc02 = pulox(cmd.get_mac())
            if cmd.get_verbose():
                pc02.set_verbose(cmd.get_verbose())
            if cmd.get_log_file_name():
                pc02.set_log_file_name(cmd.get_log_file_name())
            pc02.set_o2_low_action(cmd.get_o2_low_action(), cmd.get_o2_min())
            pc02.set_o2_high_action(cmd.get_o2_high_action(), cmd.get_o2_max())
            pc02.set_sensor_off_action(cmd.get_sensor_off_action())
            pc02.set_sensor_idle_action(cmd.get_sensor_idle_action())
            while not pc02.connect():
                print("Wait")
                time.sleep(2)
            # Request manufacturer
            if cmd.show_manufact():
                pc02.print_manufact()
            # Request device info
            if cmd.is_info():
                pc02.tx_request_info()
                pc02.wait_for_notifications(cmd.get_num_events())
            elif cmd.get_num_events() != 0:
                pc02.tx_request_io()
                pc02.wait_for_notifications(cmd.get_num_events())
            pc02.cleanup()
            print('Done')
            sys.exit(0)
        except KeyboardInterrupt as e:
            print(f'Stop {e}')
            sys.exit(-1)
        except gi.repository.GLib.GError as e:
            if e.matches(gi.repository.Gio.io_error_quark(), gi.repository.GLib.DBus.Error.NoReply):
                print(f'Disconnected')
            print(f'GErr: {e}')
        except KeyError as e:
            print(f'KeyErr: {e}')
        except Exception as e:
            print(f'Ex: {e}')

# EOF
