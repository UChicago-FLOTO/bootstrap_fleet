
import requests
from pydbus import SystemBus
import logging
import os
from collections.abc import Mapping

LOG = logging.getLogger(__name__)
logging.basicConfig()


OUTPUT_TTY="tty0"
TTY_SERVICE=f"getty@{OUTPUT_TTY}.service"
TTY_DEVICE=f"/dev/{OUTPUT_TTY}"

# ensure we write to correct TTY
with open(TTY_DEVICE, 'rb') as inf, open(TTY_DEVICE, 'wb') as outf:
    os.dup2(inf.fileno(), 0)
    os.dup2(outf.fileno(), 1)
    os.dup2(outf.fileno(), 2)

# import after setting tty
import curses



# If "replace" the call will start the unit and its dependencies,
# possibly replacing already queued jobs that conflict with this.
SYSTEMD_API_MODE="replace"

BALENA_SUPERVISOR_ADDRESS=os.environ.get("BALENA_SUPERVISOR_ADDRESS")
BALENA_SUPERVISOR_API_KEY=os.environ.get("BALENA_SUPERVISOR_API_KEY")

def _query_balena_supervisor(session: requests.Session) -> Mapping:
    headers = {"Content-Type":"application/json"}
    params={"apikey": BALENA_SUPERVISOR_API_KEY}

    url = f"{BALENA_SUPERVISOR_ADDRESS}/v1/device"
    result = session.get(url=url, headers=headers, params=params)
    data = result.json()
    return data

def main():

    bus = SystemBus()
    systemd = bus.get(".systemd1")


    # quit the plymouth (balena logo) service so that we can see the TTY
    plymouth_status = systemd.StartUnit("plymouth-quit.service", SYSTEMD_API_MODE)

    # restart getty so something is listening
    getty_status = systemd.StartUnit(TTY_SERVICE, SYSTEMD_API_MODE)

    sess = requests.session()

    # get curses window after initializing tty
    stdscr = curses.initscr()

    # Main update loop
    while True:
        supervisor_data = _query_balena_supervisor(session=sess)
        ip_address = supervisor_data.get("ip_address")
        hostname = os.environ.get("HOSTNAME")

        # Clear screen
        # stdscr.clear()
        stdscr.erase()

        # update buffer
        stdscr.addstr(f"Local IP address: {ip_address}")
        stdscr.addstr("\n")
        stdscr.addstr(f"Hostname: {hostname}")

        # refresh screen to display buffer
        stdscr.refresh()

if __name__ == "__main__":
    # clean up ncurses term settings on exit
    main()
