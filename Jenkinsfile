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
                    ]]
                ])
            }
        }

        stage('Resolve Version Tag') {
            steps {
                script {
                    env.IMAGE_TAG = "v" + sh(
                        script: "git rev-parse --short HEAD",
                        returnStdout: true
                    ).trim()
                    echo "Git commit: ${env.IMAGE_TAG}"
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

        stage('Approval') {
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    input message: "Deploy ${env.IMAGE_TAG} to production?",
                          ok: 'Deploy Now'
                }
            }
        }

        stage('Helm Deploy') {
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
        aborted {
            echo "⚠️ Deployment was rejected at approval stage."
        }
        always {
            script {
                if (env.IMAGE_TAG) {
                    // Remove local docker image
                    sh "docker rmi ${ECR_IMAGE}:${IMAGE_TAG} || true"

                    // Remove dangling/unused docker images
                    sh "docker image prune -f || true"

                    // Keep only last 5 images in ECR, delete older ones
                    sh """
                        aws ecr describe-images \
                            --repository-name ${ECR_REPO_NAME} \
                            --region ${AWS_REGION} \
                            --query 'sort_by(imageDetails, &imagePushedAt)[*].imageDigest' \
                            --output text | tr '\\t' '\\n' | head -n -5 | \
                        while read digest; do
                            aws ecr batch-delete-image \
                                --repository-name ${ECR_REPO_NAME} \
                                --region ${AWS_REGION} \
                                --image-ids imageDigest=\$digest || true
                        done
                    """
                }
            }
            cleanWs()
        }
    }

}