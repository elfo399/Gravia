pipeline {
    agent { label 'raspberry-pi && docker' }

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 45, unit: 'MINUTES')
    }

    triggers { githubPush() }

    stages {
        stage('Scarica main') {
            steps {
                checkout scm
                sh 'git log -1 --format="Commit: %h %s"'
            }
        }
        stage('Test, compila e aggiorna Gravia') {
            steps {
                sh 'sh ci/pipeline.sh'
            }
        }
    }

    post {
        always {
            junit testResults: 'reports/*.xml', allowEmptyResults: true
        }
        success { echo 'Gravia aggiornata e verificata. Configurazione e dati restano nella cartella persistente.' }
        failure { echo 'Aggiornamento non riuscito: controllare il log. Nessun dato viene eliminato dal job.' }
    }
}
