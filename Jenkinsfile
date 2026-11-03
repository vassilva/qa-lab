// Pipeline do QA Lab: Build → testes → QA → UAT → aprovação go/no-go
// A mesma imagem (qa-lab:<versão>-<commit>) é testada em QA e promovida para UAT sem ser reconstruída.

pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  stages {
    stage('Preparar') {
      steps {
        script {
          def version = readFile('VERSION').trim()
          def sha = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
          env.APP_VERSION = "${version}-${sha}"
          env.IMAGE = "qa-lab:${env.APP_VERSION}"
          currentBuild.displayName = "#${env.BUILD_NUMBER} · v${env.APP_VERSION}"
        }
        sh 'rm -rf reports && mkdir -p reports'
        echo "Versão a validar: ${env.APP_VERSION}"
      }
    }

    stage('Build da imagem') {
      steps {
        sh 'docker build -t "$IMAGE" .'
      }
    }

    stage('Testes unitários e de API') {
      steps {
        sh 'bash scripts/ci_unit_tests.sh "$IMAGE"'
      }
    }

    stage('Deploy QA') {
      steps {
        sh 'bash scripts/deploy.sh qa "$APP_VERSION"'
      }
    }

    stage('Smoke QA') {
      steps {
        sh 'docker exec qa-lab-qa-app bash scripts/smoke.sh'
      }
    }

    stage('Regressão BDD (QA)') {
      steps {
        sh 'docker exec qa-lab-qa-app bash scripts/run_tests.sh bdd'
        sh 'mkdir -p reports/qa && docker cp qa-lab-qa-app:/opt/qa-lab/reports/. reports/qa/ || true'
      }
    }

    stage('Deploy UAT') {
      steps {
        sh 'bash scripts/deploy.sh uat "$APP_VERSION"'
      }
    }

    stage('Smoke UAT') {
      steps {
        sh 'docker exec qa-lab-uat-app bash scripts/smoke.sh'
      }
    }

    stage('Aprovação go/no-go') {
      steps {
        timeout(time: 1, unit: 'DAYS') {
          input message: "A versão ${env.APP_VERSION} está em UAT. Aprovar a release?", ok: 'Go'
        }
        echo "Release ${env.APP_VERSION} aprovada."
      }
    }
  }

  post {
    always {
      junit allowEmptyResults: true, testResults: 'reports/**/*.xml'
      archiveArtifacts allowEmptyArchive: true, artifacts: 'reports/**'
    }
    success {
      echo "Pipeline concluído: ${env.APP_VERSION} aprovada em UAT."
    }
    failure {
      echo 'Pipeline falhou: ver o estágio a vermelho, os logs e os relatórios arquivados.'
    }
  }
}
