#!/bin/sh
# Jenkins entry point; keep the UI to checkout plus one update stage.
set -eu

revision=$(git rev-parse HEAD)
short_revision=$(printf '%.12s' "$revision")
run_id="gravia-ci-${BUILD_NUMBER:?Missing Jenkins BUILD_NUMBER}-$short_revision"
image="gravia:$short_revision-$BUILD_NUMBER"
directory=${GRAVIA_DEPLOY_DIRECTORY:-"$HOME/gravia"}

# Clear previous reports before any check, including failed preflight checks.
mkdir -p reports
rm -f reports/backend.xml reports/frontend.xml
finish() {
    result=$?
    trap - EXIT
    docker image rm "$run_id-backend" "$run_id-frontend" > /dev/null 2>&1 || true
    exit "$result"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo 'Verifica agent Raspberry'
test "$(uname -s)" = Linux
docker info > /dev/null
docker compose version
command -v flock
case "$(docker info --format '{{.Architecture}}')" in
    aarch64|arm64) ;;
    *) echo 'Serve un agent Docker ARM64 sul Raspberry.' >&2; exit 1 ;;
esac

echo 'Test backend'
sh ci/test.sh backend "$run_id"
echo 'Test e build frontend'
sh ci/test.sh frontend "$run_id"

echo 'Build immagine ARM64'
docker build --label "org.opencontainers.image.revision=$revision" \
    --label 'org.opencontainers.image.source=https://github.com/elfo399/Gravia' \
    -f docker/Dockerfile -t "$image" .

echo 'Aggiornamento Gravia sul Raspberry'
sh ci/bootstrap.sh "$directory" "$image" \
    "${GRAVIA_INITIAL_BOARD_MAC:-00:24:44:6C:0D:A2}" "${GRAVIA_INITIAL_HTTP_PORT:-8081}"
sh ci/deploy.sh deploy "$directory" "$image"
