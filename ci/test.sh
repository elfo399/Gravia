#!/bin/sh
# No host bind mounts: works even when the Jenkins agent itself runs in Docker.
set -eu

suite=${1:?Usage: sh ci/test.sh backend|frontend run-id}
run_id=${2:?Missing run-id}
case "$run_id" in
    gravia-ci-*[!a-zA-Z0-9-]*|'') echo 'Invalid CI run-id' >&2; exit 2 ;;
    gravia-ci-*) ;;
    *) echo 'CI run-id must start with gravia-ci-' >&2; exit 2 ;;
esac
container="$run_id-$suite"
image="$run_id-$suite"
mkdir -p reports

case "$suite" in
    backend)
        target=backend-tools
        command='ruff check . /host && ruff format --check . /host && GRAVIA_DATABASE_URL=sqlite:////tmp/migration-check.db alembic upgrade head && GRAVIA_DATABASE_URL=sqlite:////tmp/migration-check.db alembic check && pytest -q --junitxml=/tmp/backend.xml'
        ;;
    frontend)
        target=frontend-build
        command='pnpm lint && pnpm exec vitest run --reporter=default --reporter=junit --outputFile=/tmp/frontend.xml'
        ;;
    *) echo 'Unknown test suite' >&2; exit 2 ;;
esac

docker build --target "$target" -f docker/Dockerfile -t "$image" .
docker create --name "$container" "$image" sh -c "$command" > /dev/null
finish() {
    result=$?
    trap - EXIT
    # The report may not exist if lint failed before tests. Preserve the original exit code.
    docker cp "$container:/tmp/$suite.xml" "reports/$suite.xml" 2>/dev/null || true
    docker rm -f "$container" > /dev/null 2>&1 || true
    exit "$result"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
docker start --attach "$container"
exit "$(docker inspect --format '{{.State.ExitCode}}' "$container")"
