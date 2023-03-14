import csv
import curses
import logging
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping

import requests
from pydbus import SystemBus

LOG = logging.getLogger(__name__)
logging.basicConfig()


OUTPUT_TTY = "tty0"
TTY_SERVICE = f"getty@{OUTPUT_TTY}.service"
TTY_DEVICE = f"/dev/{OUTPUT_TTY}"

# ensure we write to correct TTY
with open(TTY_DEVICE, "rb") as inf, open(TTY_DEVICE, "wb") as outf:
    os.dup2(inf.fileno(), 0)
    os.dup2(outf.fileno(), 1)
    os.dup2(outf.fileno(), 2)


# If "replace" the call will start the unit and its dependencies,
# possibly replacing already queued jobs that conflict with this.
SYSTEMD_API_MODE = "replace"

BALENA_SUPERVISOR_ADDRESS = os.environ.get("BALENA_SUPERVISOR_ADDRESS")
BALENA_SUPERVISOR_API_KEY = os.environ.get("BALENA_SUPERVISOR_API_KEY")

LABELS_PATH = "/mnt/external/floto_labels.csv"
LABEL_HEADERS = [
    "labelname",
    "uuid",
    "mac_addr_list",
]


def _query_balena_supervisor(
    session: requests.Session, url=None, params=None
) -> Mapping:
    headers = {"Content-Type": "application/json"}
    params = {"apikey": BALENA_SUPERVISOR_API_KEY}

    result = session.get(url=url, headers=headers, params=params)
    data = result.json()
    return data


def get_device_info(session):
    try:
        result = _query_balena_supervisor(
            session=session,
            url=f"{BALENA_SUPERVISOR_ADDRESS}/v1/device",
        )
    except requests.JSONDecodeError as ex:
        raise ex
    else:
        return result


def get_device_name(session):
    try:
        result = _query_balena_supervisor(
            session=session,
            url=f"{BALENA_SUPERVISOR_ADDRESS}/v2/device/name",
        )
    except requests.JSONDecodeError as ex:
        raise ex
    else:
        return result.get("deviceName")


def read_and_update_labels_csv(filename, uuid, mac_address_list):
    data = []
    match = {}
    updated = False

    with open(filename, "r") as f:
        reader = csv.DictReader(f, fieldnames=LABEL_HEADERS)
        data.extend(reader)

    for idx, row in enumerate(data):
        if row.get("uuid") == uuid:
            match = row
            print(f"found match at row {idx}")
            return match
    else:
        print(f"match not found, picking first free label")

    # don't assume csv is sorted, pick first free if no match
    for row in data:
        if not row.get("uuid"):
            row["uuid"] = uuid
            row["mac_addr_list"] = mac_address_list
            match = row
            break
    # write file since we updated it
    with open(filename, "w") as f:
        writer = csv.DictWriter(f, fieldnames=LABEL_HEADERS)
        writer.writerows(data)

    return match


def find_usb_drive_path():
    cmd = ["blkid"]
    result = subprocess.run(cmd, check=True, capture_output=True)
    blkid_output = result.stdout.decode()

    try:
        matching_device = re.search("(/dev/sd.*):", blkid_output).group(1)
    except AttributeError:
        return None
    else:
        return matching_device


def mount_usb_drive(usb_path):
    mkdir_cmd = ["mkdir", "-p", "/mnt/external"]
    mkdir_result = subprocess.run(mkdir_cmd, check=True)

    with open("/etc/mtab", "r") as mtab:
        mtab_data = "\n".join(mtab.readlines())
        mnt_in_mtab = re.match("(/mnt/external)", mtab_data)
        usb_in_mtab = re.match(f"({usb_path})", mtab_data)

        if mnt_in_mtab and usb_in_mtab:
            return usb_path
        elif mnt_in_mtab and not usb_in_mtab:
            cmd = ["umount", "/mnt/external"]
            subprocess.run(cmd, check=True)

        if usb_path:
            cmd = ["mount", usb_path, "/mnt/external"]
            try:
                result = subprocess.run(cmd, check=True, capture_output=True)
            except subprocess.CalledProcessError as ex:
                return ex.stderr.decode()
            else:
                return result.stdout.decode()


def main():
    # initialize systemd services to print to print tty0 to screen
    bus = SystemBus()
    systemd = bus.get(".systemd1")
    # quit the plymouth (balena logo) service so that we can see the TTY
    systemd.StartUnit("plymouth-quit.service", SYSTEMD_API_MODE)
    # restart getty so something is listening
    systemd.StartUnit(TTY_SERVICE, SYSTEMD_API_MODE)

    # create session to contact supervisor
    sess = requests.session()

    # get curses window after initializing tty
    stdscr = curses.initscr()

    # clear any existing content from boot and prompt
    stdscr.clear()

    # query environment varibles. These shoudldn't change after the container is started
    device_uuid = os.environ.get("BALENA_DEVICE_UUID")

    while True:
        # gather updated information by calling supervisor API
        device_info = get_device_info(session=sess)

        ip_address = device_info.get("ip_address")
        mac_address_list = device_info.get("mac_address")

        usb_path = find_usb_drive_path()
        if not usb_path:
            stdscr.addstr(f"USB drive not found, restarting container\n")
            stdscr.refresh()
            sys.exit(1)
        else:
            stdscr.addstr(f"discovered drive: {usb_path}\n")

        mount_status = mount_usb_drive(usb_path)
        stdscr.addstr(f"mount status: {mount_status}\n")

        try:
            device_label = read_and_update_labels_csv(
                filename=LABELS_PATH,
                uuid=device_uuid,
                mac_address_list=mac_address_list,
            )
        except FileNotFoundError:
            stdscr.addstr(
                f"Labels file not found! Please insert usb with 'floto_labels.csv'\n"
            )
            stdscr.refresh()
            time.sleep(1)
            stdscr.clear()
            continue

        # Clear screen using erase to avoid flickering
        stdscr.clear()
        ##################################################################

        # create formatted strings, send to buffer
        stdscr.addstr(f"Saved identifiers: \n")
        for k, v in device_label.items():
            stdscr.addstr(f"\t {k}: {v}\n")

        label_name = device_label.get("labelname")
        stdscr.addstr(f"\nLabel device with {label_name}\n")

        # refresh screen to display buffer
        stdscr.refresh()
        time.sleep(5)


if __name__ == "__main__":
    main()
