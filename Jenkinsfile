pipeline {
    agent any

    environment {
        GITHUB_REPO           = 'sesu808/kubernates-demo'
        GITHUB_REPO_URL       = 'https://github.com/sesu808/kubernates-demo.git'
        GITHUB_BRANCH         = 'main'
        GITHUB_CREDENTIALS_ID = 'github-pat'

        AWS_REGION            = 'ap-south-1'
        AWS_ACCOUNT_ID        = '123456789012'
        ECR_REPO_NAME         = 'kubernates-demo'
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
                    ]]
                ])
            }
        }

        stage('Resolve Version Tag') {
            steps {
                script {
                    env.IMAGE_TAG = sh(
                        script: "git describe --tags --abbrev=0",
                        returnStdout: true
                    ).trim()
                    env.CHART_VERSION = env.IMAGE_TAG.replaceAll(/^v/, '')
                    echo "Git tag      : ${env.IMAGE_TAG}"
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
                        git push https://${GIT_USER}:${GIT_TOKEN}@github.com/${GITHUB_REPO}.git HEAD:${GITHUB_BRANCH}
                    """
                }
            }
        }

        stage('Helm Deploy') {
            when {
                expression { env.IMAGE_TAG ==~ /^v\d+\.\d+\.\d+$/ }
            }
            steps {
                sh """
                    helm upgrade --install kubernates-demo ${HELM_CHART_PATH} \
                        --namespace production \
                        --create-namespace \
                        --set image.repository=${ECR_IMAGE} \
                        --set image.tag=${IMAGE_TAG} \
                        --wait --timeout 5m
                """
            }
        }
    }

    post {
        success {
            echo "✅ Successfully built, pushed to ECR, and updated Helm chart to ${env.IMAGE_TAG}"
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