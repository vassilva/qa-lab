// QA Lab pipeline (runs on main after a pull request is merged on GitHub):
//   Build → component tests → QA (deploy, smoke, BDD regression) → test summary
//   → QA approval "Deploy to UAT?" → UAT (deploy, smoke) → release
//   If the UAT smoke fails, the pipeline stops and UAT is rolled back to the version it had before.
// The same image (qa-lab:<version>-<commit>) is tested in QA and promoted to UAT without being rebuilt.
// Triggers: every merge to main on GitHub (polled every 2 min), manual, and a nightly QA regression
// (weekdays around 02:00, which does not go on to UAT). Pull requests are checked by GitHub Actions.

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

    stage('Test summary') {
      steps {
        sh 'python3 scripts/test_summary.py reports "$APP_VERSION"'
      }
    }

    stage('Approval · Deploy to UAT?') {
      when { not { triggeredBy 'TimerTrigger' } }
      steps {
        timeout(time: 1, unit: 'DAYS') {
          input message: "QA passed for ${env.APP_VERSION} (smoke + BDD regression, see Test summary). Deploy to UAT?",
                ok: 'Deploy to UAT'
        }
        script {
          // Version UAT is running now: the rollback target if the new version fails its smoke test
          env.UAT_PREVIOUS = sh(script: "docker inspect -f '{{.Config.Image}}' qa-lab-uat-app 2>/dev/null | sed 's/^qa-lab://' || true",
                                returnStdout: true).trim()
          echo "UAT is running ${env.UAT_PREVIOUS ?: 'nothing yet'}; deploying ${env.APP_VERSION}."
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
      post {
        failure {
          script {
            if (env.UAT_PREVIOUS && env.UAT_PREVIOUS != env.APP_VERSION) {
              echo "UAT smoke FAILED for ${env.APP_VERSION}: rolling UAT back to ${env.UAT_PREVIOUS}."
              sh 'QA_LAB_CHALLENGE=0 bash scripts/deploy.sh uat "$UAT_PREVIOUS" && docker exec qa-lab-uat-app bash scripts/smoke.sh'
              currentBuild.description = "${currentBuild.description} · UAT ROLLED BACK to ${env.UAT_PREVIOUS}"
            } else {
              echo 'UAT smoke FAILED and there is no previous version to roll back to: UAT needs manual attention.'
            }
          }
        }
      }
    }

    stage('Release') {
      when { not { triggeredBy 'TimerTrigger' } }
      steps {
        echo "Release ${env.APP_VERSION} is live in UAT (smoke passed)."
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
          echo "Pipeline finished: ${env.APP_VERSION} deployed to UAT and smoke-tested."
        }
      }
    }
    failure {
      echo 'Pipeline failed: check the red stage, the Tests tab and the archived reports. A failure in a "QA · …" stage or earlier means the version did not reach UAT; a failure in "UAT · Smoke" rolled UAT back to the previous version.'
    }
  }
}
