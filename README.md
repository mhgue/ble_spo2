# Python application for use with a Pulox Checkme O2 BLE blood oxygen saturation sensor

This python application can connect via BLE to a Pulox Checkme O2 to measure [blood oxygen saturation](https://en.wikipedia.org/wiki/Oxygen_saturation_(medicine)) (SpO2), [heard rate](https://en.wikipedia.org/wiki/Pulse) (rpm) and motion or count steps.
Beside the original mobile app [ViHealth](https://play.google.com/store/apps/details?id=com.viatom.vihealth) this application provides the ability of realtime reaction to measured values reaching thresholds.

## Caution
The data provided by this application is not intended for medical use. Always consult your doctor if you have any health problems.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Hardware
There is a bunch of oximeters all running with the same firmware.
This software is developed using a

* [pulox by Viatom Checkme O2](https://www.pulox.de/pulox-by-Viatom-Checkme-O2-smartes-Handgelenk-Pulsoximeter-mit-Ringsensor)

It may work but is not tested with:

* [Viatom SleepU Pulse Oximeter](https://www.viatomtech.com/po3)

and maybe others too

## Shorts
* **HCI** is the [bluetooth host controller interface](https://en.wikipedia.org/wiki/List_of_Bluetooth_protocols#HCI) (hci) to be used (e.g. `hci0` or `hci1` ).
* **HCI-MAC** is the [media access control address](https://en.wikipedia.org/wiki/MAC_address) (MAC) of the HCI (e.g. `D8:FC:93:12:34:56` ). It is used to identify the local interface uesed to connect to the remote sensor.
* **DEV-MAC** is the BLE device media access control address (e.g. `DA:1C:F9:12:34:56` ). It is used to identify the SpO2 sensor to be used.

## Install
You can install the requirements in your python3 installation using
* `pip3 install -r requirements.txt`
or you can create a virtual python environment to run this application in.
```bash
python3 -m venv ble_spo2
source ble_spo2/bin/activate
pip3 install -r requirements.txt
```
or just call `./setup.sh` .

For using speech output as an action reaching limits, there needs to be a speech tool.
On debian systems you can install `espeak`:
* `sudo apt-get install espeak
There are other option too, see Actions below.

## Using BLE with Ubuntu Linux
Check if radio frequency (RF) devices are blocked

* `rfkill list`

Unblock all RF devices

* `rfkill unblock all`

If using a secondary bluetooth host control interface (hci) (e.g. as USB stick) do activate

* `sudo hciconfig HCI up`

Check bluetooth service running

* `sudo service bluetooth status`

You should find your blood oxygen sensor like that

    `DA:1C:F9:12:34:56 O2 0106`


Start bluetooth control, select your local hci to use, scan and **trust** your remote device.

    bluetoothctl
    [bluetooth]# list
    [bluetooth]# select HCI-MAC
    [bluetooth]# power on
    [bluetooth]# scan on
    [bluetooth]# trust DEV-MAC
    [bluetooth]# scan off
    [bluetooth]# exit

If you get the message `Connection successful` your are ready to use this script.

### Others
Start scanning for BLE devices using a hci (e.g. `hci1` or `hci0` for buildin) and stop with Ctrl-C

* `sudo hcitool -i hci1 lescan`

Add your device to BLE accept list

* `sudo hcitool -i hci1 lealadd DA:1C:F9:12:34:56`

Remove your device from BLE accept list

* `sudo hcitool -i hci1 lealrm DA:1C:F9:12:34:56`

Get some information on your device:

* `sudo hcitool -i hci1 leinfo DA:1C:F9:12:34:56`

Devices that do support pairing (not Pulox Checkme O2):

    bluetoothctl
    [bluetooth]# list
    [bluetooth]# select D8:FC:93:12:34:56
    [bluetooth]# power on
    [bluetooth]# scan on
    [bluetooth]# scan off
    [bluetooth]# pair DA:1C:F9:12:34:56
    [bluetooth]# paired-devices
    [bluetooth]# exit

`bluetoothctl` has submenus e.g. to inspect GATT data, see `menu gatt`

### Trouble
If you get no reaction at alll, make sure that the display of the device is turned on.
A Pulox Checkme O2 can only be connected by BLE as long as the 


* `GDBus.Error:org.bluez.Error.Failed: le-connection-abort-by-local`
* You see the device with `[NEW]` followed by `[DEL]`.

This is a bug in BlueZ that can be worked around by restarting the service:

* `sudo service bluetooth stop`
* `sudo service bluetooth start`
* `sudo service bluetooth status`

Getting
* `g-io-error-quark: GDBus.Error:org.bluez.Error.Failed: Input/output error (36)`
your SpO2 device is not initialized (see Using BLE with Ubuntu Linux) or blocked.
To unblock do `rfkill unblock all`.

## Actions
Any command for the underlying shell can be used for action to take place is threshold is reached.
For example:
* `spd-say -l EN "oxigen low" -i +100` *for speech output*
* `espeak -v de "Sauerstoff niedrig"` *for german speech using `espeak`*
* `aplay /usr/share/sounds/purple/alert.wav`*for audio file output or using `paplay` for pulse audio*
Your can even let your phone ring using commands to access your router.

A sample usage with english, german and spanish speach can be found in `spo2_monitor.sh`.

## ToDo
* Additional actions for
  * Pulse limit
  * Battery low
  * Connection lost
* File download of logged data

## Sensor API
For all BLE devices the 16 bit UUIDs are just a short for `0000xxxx-0000-1000-8000-00805F9B34FB`.

These pulse oximeter are using a streaming packet protocol in a UART like manner.
Therefor an RX and a TX UUID is used:
* RX: 0734594a-a8e7-4b1a-a6b1-cd5243059a57
* TX: 8b00ace7-eb0b-49b0-bbe9-9aee0a26e1a3
[Lokking for these two UUIDs](https://www.google.com/search?q=0734594a-a8e7-4b1a-a6b1-cd5243059a57+8b00ace7-eb0b-49b0-bbe9-9aee0a26e1a3) will show you projects doing similar things.

The packet protocol is based on a one byte command and this looking at the different replies is interesting to find your specific devices capabilities. For my Pulox Checkme O2 these are:

* `self.tx_cmd(0x03)` 55 01fe 0000 0400 09000000 5d (file error)
* `self.tx_cmd(0x04)` 55 01fe 0000 0000 080000830500008d050000970500000000000000000000000000000000000009090000a105000000 f9 ???
* `self.tx_cmd(0x05)` (file close)
* `self.tx_cmd(0x10)` 55 01fe 0000 0400 0b000000 71 (error)
* `seff.tx_cmd(0x14)` 55 00ff 0000 0002 `JSON string with list of files filled with zero` CRC
* `self.tx_cmd(0x15)` 55 00ff 0000 0400 00000000 ea (ack)
* `self.tx_cmd(0x16)` 55 00ff 0000 0400 00000000 ea (ack)
* `self.tx_cmd(0x17)` 55 00ff 0000 0d00 60480000000000140301000000 5a (sensor values)
                      data u8:SpO2, u8:heart_rate (bpm), u8:flag, u32:steps, u8:battery (%), u8:?, u8:moves
* `self.tx_cmd(0x18)`  # 55 00ff 0000 0400 00000000 ea (ack); (device reset)
* `self.tx_cmd(0x1B)`  # 55 00ff 0000 8900 614100130300000000007d00 n*0x7a 3f m*0x33 e4

In sleep mode moves per time period are reported to monitor restlessness during sleep.
In monitor mode the devices approximates the steps done.

Inside of the JSON string e.g.
```json
    {
    "BootloaderVer": "0.1.0.0",
    "BranchCode": "21060000",
    "CurBAT": "98%",
    "CurBatState": "0",
    "CurMode": "0",
    "CurMotor": "50",
    "CurOxiThr": "90",
    "CurPedtar": "99999",
    "CurState": "2",
    "CurTIME": "2023-02-19,12:33:11",
    "FileList": "20230219114922,20230219115633,20230219120542,",
    "FileVer": "3",
    "HardwareVer": "AA",
    "Model": "1641",
    "Region": "CE",
    "SN": "2207123456",
    "SPCPVer": "1.4",
    "SoftwareVer": "4.7.0"
    }
```
we can get the `FileList` of files with logged data that can be downloaded (not yet implemented).

## Credits
* [Talking to a Bluetooth (BLE) Pulse Oximeter](https://afshari.lu/post/211-oximeter/) *so this may work for Viatom SleepU Pulse Oximeter too (not tested)*
* [Python BLE client for Wellue / Viatom pulse oximeters](https://github.com/MackeyStingray/o2r)

## References
* [A sample Python project](https://github.com/pypa/sampleproject) *for packaging python*

## Using BLE with python
* [BLE GATT](https://github.com/ukBaz/BLE_GATT) *for using BLE from within python via BlueZ D-Bus API*
* [BLE via D-Bus](https://stackoverflow.com/questions/68643048/read-and-notification-issues-with-gattlib-ble) *without BLE lib*
