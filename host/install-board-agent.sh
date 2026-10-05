#!/bin/sh
# Explicit administrative installation/update; never called by the application pipeline.
set -eu
mac=${1:?Usage: sudo sh host/install-board-agent.sh AA:BB:CC:DD:EE:FF}
test "$(id -u)" = 0 || { echo 'Run with sudo.' >&2; exit 1; }
mac=$(printf '%s' "$mac" | tr '[:lower:]' '[:upper:]')
printf '%s\n' "$mac" | LC_ALL=C grep -Eq '^([0-9A-F]{2}:){5}[0-9A-F]{2}$' || exit 2
source=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
apt-get update
apt-get install -y --no-install-recommends python3-dbus python3-gi python3-evdev
id gravia-board >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin gravia-board
install -d -m 0755 /opt/gravia-board-agent /etc/gravia
install -m 0644 "$source/gravia_board_agent.py" "$source/gravia_board_core.py" /opt/gravia-board-agent/
install -m 0644 "$source/gravia-board-agent.service" /etc/systemd/system/
printf 'GRAVIA_BOARD_MAC=%s\n' "$mac" > /etc/gravia/board-agent.env
chmod 0644 /etc/gravia/board-agent.env
lower=$(printf '%s' "$mac" | tr '[:upper:]' '[:lower:]')
# Only this board's input/HID nodes. No membership in the broad input group.
cat > /etc/udev/rules.d/70-gravia-board.rules <<EOF
SUBSYSTEM=="input", KERNEL=="event*", ATTRS{uniq}=="$lower", GROUP="gravia-board", MODE="0660"
SUBSYSTEM=="hidraw", KERNEL=="hidraw*", ATTRS{uniq}=="$lower", GROUP="gravia-board", MODE="0660"
SUBSYSTEM=="input", KERNEL=="event*", ATTRS{uniq}=="$mac", GROUP="gravia-board", MODE="0660"
SUBSYSTEM=="hidraw", KERNEL=="hidraw*", ATTRS{uniq}=="$mac", GROUP="gravia-board", MODE="0660"
EOF
device_path=/org/bluez/hci0/dev_$(printf '%s' "$mac" | tr ':' '_')
cat > /etc/dbus-1/system.d/gravia-board.conf <<EOF
<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN" "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <policy user="gravia-board">
    <deny send_destination="org.bluez"/>
    <allow send_destination="org.bluez" send_interface="org.freedesktop.DBus.ObjectManager" send_member="GetManagedObjects" send_path="/"/>
    <allow send_destination="org.bluez" send_interface="org.bluez.Device1" send_member="Disconnect" send_path="$device_path"/>
  </policy>
</busconfig>
EOF
systemctl reload dbus.service
printf 'hid_wiimote\n' > /etc/modules-load.d/gravia-wii.conf
modprobe hid_wiimote
udevadm control --reload-rules
udevadm trigger --subsystem-match=input --subsystem-match=hidraw
systemctl daemon-reload
systemctl enable --now gravia-board-agent.service
systemctl restart gravia-board-agent.service
printf '\nSet GRAVIA_BOARD_AGENT_GID=%s in the Gravia .env for docker-compose.bluez.yml.\n' "$(id -g gravia-board)"
