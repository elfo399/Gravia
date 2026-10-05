#!/bin/sh
# First install only; all later deployments preserve local configuration and data.
set -eu
directory=${1:?Missing absolute deployment directory}
image=${2:?Missing release image}
mac=${3:?Missing board MAC}
port=${4:?Missing HTTP port}
source=$(pwd -P)
case "$directory" in
    /*) ;;
    *) echo 'Deployment directory must be an absolute Linux path.' >&2; exit 2 ;;
esac
test "$directory" != / || exit 2
if [ -r "$directory/.env" ]; then
    echo 'Existing installation: preserving .env, Compose and data.'
    exit 0
fi
mkdir -p -- "$directory"
directory=$(CDPATH= cd -- "$directory" && pwd -P)
# Refuse to bootstrap over unrelated files or inside the Jenkins checkout.
test "$directory" != "$source" || exit 2
test -z "$(ls -A "$directory")" || {
    echo 'First install requires an empty directory; configure existing installations explicitly.' >&2
    exit 2
}
# Validate configuration and free port before creating persistent files.
docker run --rm -i --network host "$image" python - "$mac" "$port" <<'PY'
import re
import socket
import sys

mac, port = sys.argv[1:]
if not re.fullmatch(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", mac):
    raise SystemExit("Invalid board MAC")
if not port.isdigit() or not 1024 <= int(port) <= 65535:
    raise SystemExit("HTTP port must be between 1024 and 65535")
with socket.socket() as probe:
    probe.bind(("0.0.0.0", int(port)))
PY
mkdir "$directory/data" "$directory/docker"
cp docker-compose.yml docker-compose.raspberry.yml "$directory/"
cp docker/Dockerfile "$directory/docker/"
# Only this newly created empty data directory is changed, never an existing database.
docker run --rm --mount "type=bind,source=$directory/data,target=/data" "$image" \
    python -c 'import os; os.chown("/data", 0, 0); os.chmod("/data", 0o700)'
umask 077
sed -e 's/^GRAVIA_BOARD_MODE=.*/GRAVIA_BOARD_MODE=real/' \
    -e "s/^GRAVIA_BOARD_MAC=.*/GRAVIA_BOARD_MAC=$mac/" \
    -e "s/^GRAVIA_HTTP_PORT=.*/GRAVIA_HTTP_PORT=$port/" \
    -e "s/^GRAVIA_PORT=.*/GRAVIA_PORT=$port/" \
    .env.example > "$directory/.env"
printf '\nCOMPOSE_FILE=docker-compose.yml:docker-compose.raspberry.yml\n' >> "$directory/.env"
printf 'First installation prepared in %s; real board; HTTP port %s.\n' "$directory" "$port"
