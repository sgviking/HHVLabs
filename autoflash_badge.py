#!/usr/bin/env python

import pyudev
import os
import sys
from termcolor import cprint

ESPTOOL_PATH = "/home/esk/src/esptool"
sys.path.append(ESPTOOL_PATH)
import esptool

BAUD = 230400
FWPATH = "/home/esk/src/SaintCon2016Badge/build_artifacts/images/saintcon_nodemcu_spiffs_master-ddb0aa83a1ecdab880360c8e7cce6407c90cb75d.bin"
# FLASH_CMD = "time esptool -cd nodemcu -cp {tty} -cb 1500000 -cf {fwpath}"
FLASH_CMD = "time ~/src/esptool/esptool.py --port {tty} --baud 1500000 write_flash --verify -fm dio -fs 32m 0x00000 {fwpath}"
ESPTOOL = "~/src/esptool/esptool.py --port {tty} {command}"


class UdevHandler(object):
    def __init__(self):
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)

        # watch for TTY devices added via udev
        self.monitor.filter_by("tty")

    def wait_for_device(self):
        poll = True
        while poll:
            device = self.monitor.poll()
            if (device.action == "add" and
                    device.properties.get("ID_BUS") == "usb" and
                    device.properties.get("ID_SERIAL") == u"1a86_USB2.0-Serial"):
                # other checking here
                return device
            print("ignoring event {} for device {} ({})".format(device.action, device.sys_name, device))


if __name__ == "__main__":
    handler = UdevHandler()
    while True:
        cprint("Waiting for device", "green")
        device = handler.wait_for_device()

        cprint("New device added: {0}".format(device), "green")
        for field in ["DEVNAME", "ID_MODEL_ENC", "ID_USB_DRIVER", ]:
            print(field, device.properties.get(field))

        initial_baud = min(esptool.ESPROM.ESP_ROM_BAUD, BAUD)
        esp = esptool.ESPROM(device.properties['DEVNAME'], initial_baud)
        esp.connect()

        mac = esp.read_mac()
        mac = ':'.join(map(lambda x: '{0:02x}'.format(x), mac))

        chip_id = esp.chip_id()
        chip_id = "0x{0:08x}".format(chip_id)

        flash_id = esp.flash_id()

        flash_manuf = flash_id & 0xff
        flash_device = (flash_id & 0xff00) | (flash_id >> 16 & 0xff)

        dev_data = {
            'mac': mac,
            'chip_id': chip_id,
            'flash_id': "manuf={0:02x},dev={1:04x}".format(flash_manuf, flash_device),
        }

        del esp

        cprint('mac: {mac} chip_id: {chip_id} flash_id: {flash_id}'.format(**dev_data), 'cyan')

        cmd = FLASH_CMD.format(tty=device.properties['DEVNAME'], fwpath=FWPATH, args='')

        cprint("Flash starting", "green")
        print("CMD: {0}".format(cmd))

        ret = os.system(cmd)

        if ret != 0:
            cprint("Flash failed with {0}".format(ret), "red")
        else:
            cprint("Flash succeeded.", "green")
