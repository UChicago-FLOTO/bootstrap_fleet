import curses
import json
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


# If "replace" the call will start the unit and its dependencies,
# possibly replacing already queued jobs that conflict with this.
SYSTEMD_API_MODE = "replace"

BALENA_SUPERVISOR_ADDRESS = os.environ.get("BALENA_SUPERVISOR_ADDRESS")
BALENA_SUPERVISOR_API_KEY = os.environ.get("BALENA_SUPERVISOR_API_KEY")


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

    # Main update loop
    t = time.process_time()
    # do some stuff
    elapsed_time = time.process_time() - t

    loop_time = 0

    while True:
        # gather updated information by calling supervisor API
        device_info = get_device_info(session=sess)
        device_name_current = get_device_name(session=sess)

        ip_address = device_info.get("ip_address")
        mac_address = device_info.get("mac_address")
        d_status = device_info.get("status")

        # Clear screen using erase to avoid flickering
        stdscr.erase()

        # create formatted strings, send to buffer
        stdscr.addstr(f"Device UUID: {device_uuid} has Hostname: {hostname}\n")
        stdscr.addstr(
            f"Current Device name is: {device_name_current} and was originally: {device_name_at_init}\n"
        )
        stdscr.addstr(f"Local IP address: {ip_address}\n")
        stdscr.addstr(f"Local MAC address: {mac_address}\n")
        stdscr.addstr(f"Supervisor Status: {d_status}\n")

        current_loop_time = time.perf_counter()
        loop_duration = current_loop_time - loop_time
        fps = int(1 / loop_duration)

        loop_time = current_loop_time
        stdscr.addstr(f"Updating at {fps} FPS\n")

        # refresh screen to display buffer
        stdscr.refresh()


if __name__ == "__main__":
    # ensure we write to correct TTY
    with open(TTY_DEVICE, "rb") as inf, open(TTY_DEVICE, "wb") as outf:
        os.dup2(inf.fileno(), 0)
        os.dup2(outf.fileno(), 1)
        os.dup2(outf.fileno(), 2)
        main()
