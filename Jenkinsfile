// Pipeline do QA Lab: Build → testes de componente → QA (smoke + regressão BDD) → UAT (smoke) → go/no-go
// A mesma imagem (qa-lab:<versão>-<commit>) é testada em QA e promovida para UAT sem ser reconstruída.

pipeline {
  agent any

  parameters {
    choice(
      name: 'REGRESSAO',
      choices: ['completa', 'critica'],
      description: 'completa = todos os cenários BDD · critica = só os cenários @critico (quando o tempo é curto)'
    )
  }

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
          env.BDD_TAGS = (params.REGRESSAO == 'critica') ? '@critico' : ''
          currentBuild.displayName = "#${env.BUILD_NUMBER} · v${env.APP_VERSION}"
          currentBuild.description = "Regressão ${params.REGRESSAO ?: 'completa'}"
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

    stage('Testes de componente e API') {
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
        sh 'docker exec -e BDD_TAGS="$BDD_TAGS" qa-lab-qa-app bash scripts/run_tests.sh bdd'
      }
      post {
        always {
          sh 'mkdir -p reports/qa && docker cp qa-lab-qa-app:/opt/qa-lab/reports/. reports/qa/ || true'
        }
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

    stage('Resumo de testes') {
      steps {
        sh 'python3 scripts/test_summary.py reports "$APP_VERSION"'
      }
    }

    stage('Aprovação go/no-go') {
      steps {
        timeout(time: 1, unit: 'DAYS') {
          input message: "A versão ${env.APP_VERSION} está em UAT. Confirmaste o checklist de release (docs/qa/checklist-release.md)? Aprovar?",
                ok: 'Go'
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
      echo 'Pipeline falhou: ver o estágio a vermelho, o separador Tests e os relatórios arquivados. A versão NÃO segue para UAT.'
    }
  }
}
