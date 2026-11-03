// Pipeline do QA Lab: Build → testes de componente → QA (smoke + regressão BDD) → UAT (smoke) → go/no-go
// A mesma imagem (qa-lab:<versão>-<commit>) é testada em QA e promovida para UAT sem ser reconstruída.
// Disparos: cada commit (verificação a cada 2 min), manual, e regressão noturna em QA (dias úteis às ~02:00,
// sem passar para UAT).

pipeline {
  agent any

  parameters {
    choice(
      name: 'REGRESSAO',
      choices: ['completa', 'critica'],
      description: 'completa = todos os cenários BDD · critica = só os cenários @critico (quando o tempo é curto)'
    )
    booleanParam(
      name: 'MODO_DESAFIO',
      defaultValue: false,
      description: 'Liga os defeitos escondidos no ambiente QA (treino de análise de defeitos). A regressão vai falhar e a versão NÃO passa para UAT.'
    )
  }

  triggers {
    cron('H 2 * * 1-5')      // regressão noturna em QA, dias úteis
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
          env.QA_LAB_CHALLENGE = params.MODO_DESAFIO ? '1' : '0'
          def noturno = currentBuild.getBuildCauses('hudson.triggers.TimerTrigger$TimerTriggerCause') ? ' · noturna (só QA)' : ''
          currentBuild.description = "Regressão ${params.REGRESSAO ?: 'completa'}${params.MODO_DESAFIO ? ' · MODO DESAFIO' : ''}${noturno}"
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

    stage('QA · Deploy') {
      steps {
        sh 'QA_LAB_CHALLENGE="$QA_LAB_CHALLENGE" bash scripts/deploy.sh qa "$APP_VERSION"'
      }
    }

    stage('QA · Smoke') {
      steps {
        sh 'docker exec qa-lab-qa-app bash scripts/smoke.sh'
      }
    }

    stage('QA · Regressão BDD') {
      steps {
        sh 'docker exec -e BDD_TAGS="$BDD_TAGS" qa-lab-qa-app bash scripts/run_tests.sh bdd'
      }
      post {
        always {
          sh 'docker exec qa-lab-qa-app python scripts/test_summary.py reports "$APP_VERSION" > /dev/null || true'
          sh 'mkdir -p reports/qa && docker cp qa-lab-qa-app:/opt/qa-lab/reports/. reports/qa/ || true'
        }
      }
    }

    stage('UAT · Deploy') {
      when { not { triggeredBy 'TimerTrigger' } }
      steps {
        sh 'QA_LAB_CHALLENGE=0 bash scripts/deploy.sh uat "$APP_VERSION"'
      }
    }

    stage('UAT · Smoke') {
      when { not { triggeredBy 'TimerTrigger' } }
      steps {
        sh 'docker exec qa-lab-uat-app bash scripts/smoke.sh'
      }
    }

    stage('UAT · Resumo de testes') {
      when { not { triggeredBy 'TimerTrigger' } }
      steps {
        sh 'python3 scripts/test_summary.py reports "$APP_VERSION"'
      }
    }

    stage('UAT · Go/No-go') {
      when { not { triggeredBy 'TimerTrigger' } }
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
      junit allowEmptyResults: true, testResults: 'reports/unit/pytest-unit.xml,reports/qa/behave/*.xml'
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
