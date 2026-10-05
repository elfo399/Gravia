#!/bin/sh
# Once per board/host. Existing pairing is preserved; no remove command, no runtime connect loop.
set -eu
mac=${1:?Usage: sudo sh scripts/setup_balance_board.sh AA:BB:CC:DD:EE:FF}
printf '%s\n' "$mac" | LC_ALL=C grep -Eq '^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$' || exit 2
bluetoothctl power on
if bluetoothctl info "$mac" | grep -q 'Paired: yes'; then
    bluetoothctl trust "$mac"
    if [ "${2:-}" = --initialize-hid ]; then
        printf '\nAttendi Agent registered, premi SYNC solo per il setup e scrivi: connect %s. Dopo il LED fisso: disconnect %s, quit.\n' "$mac" "$mac"
        { printf 'power on\nagent on\ndefault-agent\n'; cat; } | bluetoothctl --agent NoInputNoOutput
    fi
else
    printf '\nPremi SYNC rosso una sola volta. Nel prompt esegui subito: pair %s, connect %s, trust %s. Poi disconnect %s, scan off, quit.\n' "$mac" "$mac" "$mac" "$mac"
    # Keep the agent and discovery alive in the same interactive bluetoothctl process.
    { printf 'power on\nagent on\ndefault-agent\nscan on\n'; cat; } | bluetoothctl --agent NoInputNoOutput
fi
bluetoothctl info "$mac"
bluetoothctl info "$mac" | grep -q 'Paired: yes'
bluetoothctl info "$mac" | grep -q 'Trusted: yes'
printf '\nPairing e trust verificati. Verifica ora OFF/ON con solo POWER frontale.\n'
