"""Match the actual HID_UNIQ uevent; hid-wiimote leaves input/uniq empty."""

import sys
from pathlib import Path


def matches_board(path, mac):
    for parent in (path, *path.parents):
        try:
            properties = dict(
                line.split("=", 1)
                for line in (parent / "uevent").read_text().splitlines()
                if "=" in line
            )
        except OSError:
            continue
        if "HID_UNIQ" in properties:
            return (
                properties["HID_UNIQ"].upper() == mac.upper()
                and properties.get("HID_ID") == "0005:0000057E:00000306"
            )
    return False


if __name__ == "__main__":
    device = (Path("/sys") / sys.argv[1].lstrip("/")).resolve()
    if Path("/sys") in device.parents and matches_board(device, sys.argv[2]):
        print("gravia-board")
    else:
        raise SystemExit(1)
