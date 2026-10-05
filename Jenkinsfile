pipeline {
    agent { label 'raspberry-pi && docker' }

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 45, unit: 'MINUTES')
    }

    triggers { githubPush() }

    parameters {
        string(name: 'DEPLOY_DIRECTORY', defaultValue: '',
            description: 'Cartella persistente sul Raspberry; vuoto usa $HOME/gravia.')
        string(name: 'BOARD_MAC', defaultValue: '00:24:44:6C:0D:A2',
            description: 'MAC della board reale, usato solo alla prima installazione.')
        string(name: 'HTTP_PORT', defaultValue: '8081',
            description: 'Porta HTTP sul Raspberry, usata solo alla prima installazione.')
    }

    stages {
        stage('Checkout main') {
            steps {
                checkout scm
                script {
                    env.REVISION = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
                    env.CI_PREFIX = "gravia-ci-${env.BUILD_NUMBER}-${env.REVISION.take(12)}"
                    env.RELEASE_IMAGE = "gravia:${env.REVISION.take(12)}-${env.BUILD_NUMBER}"
                    env.DEPLOY_DIRECTORY = params.DEPLOY_DIRECTORY.trim() ?: sh(
                        script: 'printf "%s/gravia" "$HOME"', returnStdout: true).trim()
                }
            }
        }

        stage('Preflight') {
            steps {
                sh '''
                    set -eu
                    test "$(uname -s)" = Linux
                    docker info > /dev/null
                    docker compose version
                    command -v flock
                    case "$(docker info --format '{{.Architecture}}')" in
                        aarch64|arm64) ;;
                        *) echo 'Serve un agent Docker ARM64 sul Raspberry.' >&2; exit 1 ;;
                    esac
                    rm -f reports/backend.xml reports/frontend.xml
                '''
            }
        }

        stage('Backend: Ruff + Pytest') {
            steps { sh 'sh ci/test.sh backend "$CI_PREFIX"' }
        }

        stage('Frontend: Biome + Vitest + build') {
            steps { sh 'sh ci/test.sh frontend "$CI_PREFIX"' }
        }

        stage('Build immagine ARM64') {
            steps {
                sh '''
                    set -eu
                    docker build --label "org.opencontainers.image.revision=$REVISION" \
                        --label "org.opencontainers.image.source=https://github.com/elfo399/Gravia" \
                        -f docker/Dockerfile -t "$RELEASE_IMAGE" .
                '''
            }
        }

        stage('Deploy Raspberry + healthcheck') {
            options { timeout(time: 15, unit: 'MINUTES') }
            steps {
                sh '''
                    sh ci/bootstrap.sh "$DEPLOY_DIRECTORY" "$RELEASE_IMAGE" "$BOARD_MAC" "$HTTP_PORT"
                    sh ci/deploy.sh deploy "$DEPLOY_DIRECTORY" "$RELEASE_IMAGE"
                '''
            }
        }
    }

    post {
        always {
            script {
                if (fileExists('reports/backend.xml') || fileExists('reports/frontend.xml')) {
                    junit testResults: 'reports/*.xml', allowEmptyResults: false
                }
            }
        }
        cleanup {
            sh '''
                if [ -n "${CI_PREFIX:-}" ]; then
                    docker image rm "$CI_PREFIX-backend" "$CI_PREFIX-frontend" > /dev/null 2>&1 || true
                fi
            '''
        }
    }
}
