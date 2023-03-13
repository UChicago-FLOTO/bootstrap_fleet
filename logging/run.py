import csv
import curses
import logging
import os
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


def change_hostname(session, new_hostname):
    headers = {"Content-Type": "application/json"}
    params = {"apikey": BALENA_SUPERVISOR_API_KEY}

    url = f"{BALENA_SUPERVISOR_ADDRESS}/v1/device/host-config"

    data = {"network": {"hostname": new_hostname}}

    result = requests.patch(url=url, headers=headers, params=params, json=data)
    return result


def get_labels_from_csv(filename):
    """
    Loads csv file

    Returns: (dict of populated labels by uuid, list of empty labels)
    """

    labels_list = []

    with open(filename) as csvfile:
        label_reader = csv.DictReader(csvfile)
        for item in label_reader:
            labels_list.append(item)

        return labels_list


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
    device_name_at_init = os.environ.get("RESIN_DEVICE_NAME_AT_INIT")
    hostname = os.environ.get("HOSTNAME")

    device_info = get_device_info(session=sess)
    mac_address = device_info.get("mac_address")

    # load labels
    labels_list = get_labels_from_csv(LABELS_PATH)
    device_label = {}
    found_label = False
    wrote_label = False

    # search for match in list
    for label in labels_list:
        if label.get("uuid") == device_uuid:
            device_label = label
            found_label = True
            break

    if not device_label:
        # if no match found, search for first unused label
        for idx, label in enumerate(labels_list):
            if not label.get("uuid"):
                device_label = label
                break

    device_label["mac_addr_list"] = mac_address
    device_label["uuid"] = device_uuid
    # TODO write chosen label
    # write_new_label(device_label)

    while True:
        # gather updated information by calling supervisor API
        device_info = get_device_info(session=sess)

        ip_address = device_info.get("ip_address")
        mac_address = device_info.get("mac_address")

        # Clear screen using erase to avoid flickering
        stdscr.clear()
        ##################################################################

        # create formatted strings, send to buffer
        stdscr.addstr(f"Device UUID: {device_uuid}\n")
        stdscr.addstr(f"Local MAC address: {mac_address}\n")
        stdscr.addstr(f"Local IP address: {ip_address}\n")
        label_name = device_label.get("label")
        if found_label:
            stdscr.addstr(f"Found Label in List! \n Label device with {label_name}\n")
        else:
            stdscr.addstr(
                f"Picked first free Label! \n Label device with {label_name}\n"
            )

        # refresh screen to display buffer
        stdscr.refresh()
        time.sleep(5)


if __name__ == "__main__":
    main()
