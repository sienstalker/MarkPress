// MarkPress CI/CD pipeline.
// GitHub push -> webhook -> Jenkins (on EC2) -> lint, test, build -> Nginx serves the site.

pipeline {
    agent any

    options {
        skipDefaultCheckout()          // we check out explicitly so it shows as its own stage
        disableConcurrentBuilds()      // two deploys at once could mix files
        buildDiscarder(logRotator(numToKeepStr: '15'))
    }

    triggers {
        githubPush()                   // fires when GitHub's webhook reaches Jenkins
    }

    environment {
        VENV       = "${WORKSPACE}/.venv"
        DEPLOY_DIR = '/var/www/markpress'   // folder Nginx serves; owned by the jenkins user
        SITE_URL   = 'http://localhost'
    }

    stages {
        stage('Checkout') {
            steps {
                script {
                    def scmVars = checkout scm
                    env.GIT_COMMIT = scmVars.GIT_COMMIT
                }
                sh 'git log -1 --pretty="Building commit %h: %s (%an)"'
            }
        }

        stage('Set up Python') {
            steps {
                sh '''
                    python3 -m venv "$VENV"
                    "$VENV/bin/pip" install --quiet --upgrade pip
                    "$VENV/bin/pip" install --quiet -r requirements-dev.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '"$VENV/bin/flake8" markpress tests'
            }
        }

        stage('Test') {
            steps {
                sh '''
                    mkdir -p reports
                    "$VENV/bin/pytest" \
                        --junitxml=reports/junit.xml \
                        --cov=markpress \
                        --cov-report=term-missing \
                        --cov-report=xml:reports/coverage.xml
                '''
            }
            post {
                always {
                    junit 'reports/junit.xml'
                }
            }
        }

        stage('Build site') {
            steps {
                sh '"$VENV/bin/python" -m markpress --src content --out public'
                archiveArtifacts artifacts: 'public/**', fingerprint: true
            }
        }

        stage('Deploy') {
            steps {
                sh 'rsync -a --delete public/ "$DEPLOY_DIR/"'
            }
        }

        stage('Smoke test') {
            steps {
                sh '''
                    curl -fsS "$SITE_URL/" -o reports/live-index.html
                    grep -q "Build #$BUILD_NUMBER" reports/live-index.html
                    echo "Live site is serving build #$BUILD_NUMBER"
                '''
            }
        }
    }

    post {
        success {
            echo "Deployed build #${env.BUILD_NUMBER} successfully."
        }
        failure {
            echo 'Pipeline failed. The live site still serves the last successful build.'
        }
    }
}
