pipeline {
    agent any

    options {
        disableConcurrentBuilds()
    }

    environment {
        GITHUB_REPO           = 'sesu808/kubernates-demo'
        GITHUB_REPO_URL       = 'https://github.com/sesu808/kubernates-demo.git'
        GITHUB_BRANCH         = 'main'
        GITHUB_CREDENTIALS_ID = 'github-pat'

        AWS_REGION            = 'ap-south-1'
        AWS_ACCOUNT_ID        = '624858524005'
        ECR_REPO_NAME         = 'sample-app'
        ECR_REGISTRY          = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        ECR_IMAGE             = "${ECR_REGISTRY}/${ECR_REPO_NAME}"

        HELM_CHART_PATH       = 'helm'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout([
                    $class           : 'GitSCM',
                    branches         : [[name: "*/${GITHUB_BRANCH}"]],
                    userRemoteConfigs: [[
                        url          : env.GITHUB_REPO_URL,
                        credentialsId: env.GITHUB_CREDENTIALS_ID
                    ]],
                    extensions: [[
                        $class          : 'MessageExclusion',
                        excludedMessage : '.*\\[ci skip\\].*'
                    ]]
                ])
            }
        }

        stage('Check CI Skip') {       // ← NEW: abort if Jenkins own commit
            steps {
                script {
                    def msg = sh(script: 'git log -1 --pretty=%B', returnStdout: true).trim()
                    if (msg.contains('[ci skip]')) {
                        currentBuild.result = 'NOT_BUILT'
                        error("Skipping build: [ci skip] commit detected")
                    }
                }
            }
        }

        stage('Resolve Version Tag') {
            steps {
                script {
                    env.IMAGE_TAG = "v" + sh(
                        script: "git rev-parse --short HEAD",
                        returnStdout: true
                    ).trim()
                    env.CHART_VERSION = "1.0." + sh(
                        script: "git rev-list --count HEAD",
                        returnStdout: true
                    ).trim()
                    echo "Git commit   : ${env.IMAGE_TAG}"
                    echo "Chart version: ${env.CHART_VERSION}"
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh """
                    docker build \
                        --tag ${ECR_IMAGE}:${IMAGE_TAG} \
                        .
                """
            }
        }

        stage('Push to ECR') {
            steps {
                sh """
                    aws ecr get-login-password --region ${AWS_REGION} | \
                        docker login --username AWS --password-stdin ${ECR_REGISTRY}
                    docker push ${ECR_IMAGE}:${IMAGE_TAG}
                """
            }
        }

        stage('Update Helm Chart') {
            steps {
                script {
                    sh """
                        sed -i 's/^version:.*/version: ${CHART_VERSION}/'       ${HELM_CHART_PATH}/Chart.yaml
                        sed -i 's/^appVersion:.*/appVersion: "${IMAGE_TAG}"/'   ${HELM_CHART_PATH}/Chart.yaml
                        sed -i 's|repository:.*|repository: ${ECR_IMAGE}|'      ${HELM_CHART_PATH}/values.yaml
                        sed -i 's|tag:.*|tag: "${IMAGE_TAG}"|'                  ${HELM_CHART_PATH}/values.yaml
                    """
                }
            }
        }

        stage('Commit & Push Helm Changes') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: env.GITHUB_CREDENTIALS_ID,
                    usernameVariable: 'GIT_USER',
                    passwordVariable: 'GIT_TOKEN'
                )]) {
                    sh """
                        git config user.email "jenkins@sesu808.ci"
                        git config user.name  "Jenkins CI"
                        git add ${HELM_CHART_PATH}/Chart.yaml ${HELM_CHART_PATH}/values.yaml
                        git diff --cached --quiet || \
                            git commit -m "chore: bump helm chart to ${IMAGE_TAG} [ci skip]"
                        git pull --rebase https://${GIT_USER}:${GIT_TOKEN}@github.com/${GITHUB_REPO}.git ${GITHUB_BRANCH}
                        git push https://${GIT_USER}:${GIT_TOKEN}@github.com/${GITHUB_REPO}.git HEAD:${GITHUB_BRANCH}
                    """
                }
            }
        }

        stage('Helm Deploy') {
            when {
                expression { env.IMAGE_TAG != null }
            }
            steps {
                sh """
                    helm upgrade --install kubernates-demo ${HELM_CHART_PATH} \
                        --namespace production \
                        --create-namespace \
                        --set image.repository=${ECR_IMAGE} \
                        --set image.tag=${IMAGE_TAG} \
                        --set ingress.enabled=false \
                        --set httpRoute.enabled=false \
                        --set autoscaling.enabled=false
                """
            }
        }

    }

    post {
        success {
            echo "✅ Successfully built, pushed to ECR, and deployed Helm chart ${env.IMAGE_TAG}"
        }
        failure {
            echo "❌ Pipeline failed. Check console output above."
        }
        always {
            sh "docker rmi ${ECR_IMAGE}:${IMAGE_TAG} || true"
            cleanWs()
        }
    }

}