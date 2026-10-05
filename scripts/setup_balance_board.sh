#!/bin/sh
# Once per board/host. Existing pairing is preserved; no remove command, no runtime connect loop.
set -eu
mac=${1:?Usage: sudo sh scripts/setup_balance_board.sh AA:BB:CC:DD:EE:FF}
printf '%s\n' "$mac" | LC_ALL=C grep -Eq '^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$' || exit 2
bluetoothctl power on
if bluetoothctl info "$mac" | grep -q 'Paired: yes'; then
    bluetoothctl trust "$mac"
else
    printf '\nPremi SYNC rosso una sola volta. Nel prompt esegui: pair %s, trust %s, scan off, quit.\n' "$mac" "$mac"
    # Keep the agent and discovery alive in the same interactive bluetoothctl process.
    { printf 'power on\nagent on\ndefault-agent\nscan on\n'; cat; } | bluetoothctl --agent NoInputNoOutput
fi
bluetoothctl info "$mac"
bluetoothctl info "$mac" | grep -q 'Paired: yes'
bluetoothctl info "$mac" | grep -q 'Trusted: yes'
printf '\nSetup verificato. Nell\047uso quotidiano premi soltanto POWER frontale.\n'
