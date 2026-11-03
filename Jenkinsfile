// QA Lab pipeline: Build → component tests → QA (smoke + BDD regression) → UAT (smoke) → go/no-go
// The same image (qa-lab:<version>-<commit>) is tested in QA and promoted to UAT without being rebuilt.
// Triggers: every commit (polled every 2 min), manual, and a nightly QA regression (weekdays around 02:00,
// which does not go on to UAT).

pipeline {
  agent any

  parameters {
    choice(
      name: 'REGRESSION',
      choices: ['full', 'critical'],
      description: 'full = every BDD scenario · critical = only @critical scenarios (when time is short)'
    )
    booleanParam(
      name: 'CHALLENGE_MODE',
      defaultValue: false,
      description: 'Enables the hidden defects in the QA environment (defect analysis practice). The regression will fail and the version will NOT go to UAT.'
    )
  }

  triggers {
    cron('H 2 * * 1-5')      // nightly QA regression, weekdays
  }

  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  stages {
    stage('Prepare') {
      steps {
        script {
          def version = readFile('VERSION').trim()
          def sha = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
          env.APP_VERSION = "${version}-${sha}"
          env.IMAGE = "qa-lab:${env.APP_VERSION}"
          env.BDD_TAGS = (params.REGRESSION == 'critical') ? '@critical' : ''
          currentBuild.displayName = "#${env.BUILD_NUMBER} · v${env.APP_VERSION}"
          env.QA_LAB_CHALLENGE = params.CHALLENGE_MODE ? '1' : '0'
          env.NIGHTLY = currentBuild.getBuildCauses('hudson.triggers.TimerTrigger$TimerTriggerCause') ? '1' : '0'
          currentBuild.description = "${params.REGRESSION ?: 'full'} regression${params.CHALLENGE_MODE ? ' · CHALLENGE MODE' : ''}${env.NIGHTLY == '1' ? ' · nightly (QA only)' : ''}"
        }
        sh 'rm -rf reports && mkdir -p reports'
        echo "Version under test: ${env.APP_VERSION}"
      }
    }

    stage('Build image') {
      steps {
        sh 'docker build -t "$IMAGE" .'
      }
    }

    stage('Component and API tests') {
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

    stage('QA · BDD regression') {
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

    stage('UAT · Test summary') {
      when { not { triggeredBy 'TimerTrigger' } }
      steps {
        sh 'python3 scripts/test_summary.py reports "$APP_VERSION"'
      }
    }

    stage('UAT · Go/No-go') {
      when { not { triggeredBy 'TimerTrigger' } }
      steps {
        timeout(time: 1, unit: 'DAYS') {
          input message: "Version ${env.APP_VERSION} is in UAT. Have you checked the release checklist (docs/qa/release-checklist.md)? Approve?",
                ok: 'Go'
        }
        echo "Release ${env.APP_VERSION} approved."
      }
    }
  }

  post {
    always {
      junit allowEmptyResults: true, testResults: 'reports/unit/pytest-unit.xml,reports/qa/behave/*.xml'
      archiveArtifacts allowEmptyArchive: true, artifacts: 'reports/**'
    }
    success {
      script {
        if (env.NIGHTLY == '1') {
          echo "Nightly QA regression passed for ${env.APP_VERSION}."
        } else {
          echo "Pipeline finished: ${env.APP_VERSION} approved in UAT."
        }
      }
    }
    failure {
      echo 'Pipeline failed: check the red stage, the Tests tab and the archived reports. If the failure was in a "QA · …" stage or earlier, the version did not reach UAT.'
    }
  }
}
