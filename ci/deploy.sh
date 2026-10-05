#!/bin/sh
# Deploy only the image. Compose, .env, mounts and NPM networking stay owned by the installation.
set -eu

action=${1:?Usage: sh ci/deploy.sh check|deploy /absolute/gravia image-tag}
directory=${2:?Missing deployment directory}
image=${3:?Missing release image}
scripts=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
case "$directory" in
    /*) ;;
    *) echo 'DEPLOY_DIRECTORY must be an absolute Linux path.' >&2; exit 2 ;;
esac
test "$directory" != / || { echo 'Refusing deployment in /.' >&2; exit 2; }
test -d "$directory" || { echo 'Deployment directory does not exist.' >&2; exit 2; }
cd -- "$directory"
test -r .env || { echo 'Deployment .env is missing or unreadable.' >&2; exit 2; }
docker compose config --quiet
docker compose config --services | grep -qx gravia || {
    echo 'The installation must contain service gravia.' >&2; exit 2
}
alias_image=$(docker compose config --images gravia)
case "$alias_image" in
    ''|*@*|*' '*) echo 'Expected one mutable image tag for service gravia.' >&2; exit 2 ;;
esac
test "$(printf '%s\n' "$alias_image" | wc -l)" -eq 1 || exit 2

case "$action" in
    check) printf 'Deploy configuration valid; runtime image alias: %s\n' "$alias_image"; exit 0 ;;
    deploy) ;;
    *) echo 'Unknown deployment action' >&2; exit 2 ;;
esac

command -v flock > /dev/null || { echo 'flock (util-linux) is required on the agent.' >&2; exit 2; }
docker image inspect "$image" > /dev/null
# Serialize deploys from this job, copied jobs and manual invocations.
exec 9>.gravia-deploy.lock
flock -w 300 9 || { echo 'Another Gravia deployment is running.' >&2; exit 1; }
container=$(docker compose ps --all --quiet gravia)
old_image=''
if [ -n "$container" ]; then
    test "$(printf '%s\n' "$container" | wc -l)" -eq 1 || exit 2
    old_image=$(docker inspect --format '{{.Image}}' "$container")
    if [ "$(docker inspect --format '{{.State.Running}}' "$container")" = true ]; then
        # Wait for a weighing to finish and create a consistent SQLite backup inside /data.
        docker exec -i "$container" python - "$image" < "$scripts/prepare_deploy.py"
    fi
fi

rollback() {
    result=$?
    trap - EXIT
    if [ "$result" -ne 0 ] && [ -n "$old_image" ]; then
        echo 'Deploy failed: restoring the previous image.' >&2
        if docker tag "$old_image" "$alias_image" && \
            docker compose up -d --no-deps --no-build --pull never --force-recreate \
                --wait --wait-timeout 180 gravia; then
            echo 'Previous image restored.' >&2
        else
            echo 'Rollback failed; inspect the Gravia container on the Raspberry.' >&2
        fi
    fi
    exit "$result"
}
trap rollback EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

docker tag "$image" "$alias_image"
docker compose up -d --no-deps --no-build --pull never --force-recreate \
    --wait --wait-timeout 180 gravia
docker compose exec -T gravia python - < "$scripts/verify_deploy.py"
printf 'Deployment complete: %s\n' "$image"
