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

                    env.HELM_REVISION = sh(
                        script: """
                            helm history kubernates-demo -n production --max 1 2>/dev/null | \
                            awk 'NR>1 {print \$1}' | tail -1 || echo '0'
                        """,
                        returnStdout: true
                    ).trim()
                    echo "Current stable revision: ${env.HELM_REVISION}"
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
                script {
                    try {
                        sh """
                            helm upgrade --install kubernates-demo ${HELM_CHART_PATH} \
                                --namespace production \
                                --create-namespace \
                                --set image.repository=${ECR_IMAGE} \
                                --set image.tag=${IMAGE_TAG} \
                                --wait \
                                --timeout 3m
                        """
                        echo "✅ Deployment successful"

                    } catch (err) {
                        echo "❌ Deployment failed — starting rollback..."

                        if (env.HELM_REVISION != '0') {
                            sh """
                                helm rollback kubernates-demo ${HELM_REVISION} \
                                    --namespace production \
                                    --wait
                            """
                            echo "✅ Rolled back to revision ${env.HELM_REVISION}"

                            sh """
                                WEBHOOK=\$(cat /var/lib/jenkins/slack_webhook.txt)
                                curl -X POST \$WEBHOOK \
                                    -H 'Content-Type: application/json' \
                                    -d '{
                                        "text": "⚠️ *Rollback Triggered*\\n*Job:* ${env.JOB_NAME}\\n*Build:* #${env.BUILD_NUMBER}\\n*Failed Version:* ${env.IMAGE_TAG}\\n*Rolled Back To Revision:* ${env.HELM_REVISION}\\n*URL:* ${env.BUILD_URL}"
                                    }'
                            """
                        } else {
                            echo "⚠️ No previous revision found — skipping rollback"
                        }

                        error("Deployment failed — rolled back to revision ${env.HELM_REVISION}")
                    }
                }
            }
        }

    }

    post {
        success {
            echo "✅ Successfully deployed ${env.IMAGE_TAG}"
            sh """
                WEBHOOK=\$(cat /var/lib/jenkins/slack_webhook.txt)
                curl -X POST \$WEBHOOK \
                    -H 'Content-Type: application/json' \
                    -d '{
                        "text": "✅ *Deployment Successful*\\n*Job:* ${env.JOB_NAME}\\n*Build:* #${env.BUILD_NUMBER}\\n*Version:* ${env.IMAGE_TAG}\\n*Duration:* ${currentBuild.durationString}\\n*URL:* ${env.BUILD_URL}"
                    }'
            """
        }
        failure {
            echo "❌ Pipeline failed."
            sh """
                WEBHOOK=\$(cat /var/lib/jenkins/slack_webhook.txt)
                curl -X POST \$WEBHOOK \
                    -H 'Content-Type: application/json' \
                    -d '{
                        "text": "❌ *Pipeline Failed*\\n*Job:* ${env.JOB_NAME}\\n*Build:* #${env.BUILD_NUMBER}\\n*Version:* ${env.IMAGE_TAG ?: 'N/A'}\\n*Duration:* ${currentBuild.durationString}\\n*URL:* ${env.BUILD_URL}"
                    }'
            """
        }
        aborted {
            echo "⚠️ Deployment rejected at approval."
            sh """
                WEBHOOK=\$(cat /var/lib/jenkins/slack_webhook.txt)
                curl -X POST \$WEBHOOK \
                    -H 'Content-Type: application/json' \
                    -d '{
                        "text": "⚠️ *Deployment Aborted*\\n*Job:* ${env.JOB_NAME}\\n*Build:* #${env.BUILD_NUMBER}\\n*Version:* ${env.IMAGE_TAG ?: 'N/A'}\\n*Reason:* Rejected at approval stage"
                    }'
            """
        }
        always {
            script {
                if (env.IMAGE_TAG) {
                    sh "docker rmi ${ECR_IMAGE}:${IMAGE_TAG} || true"
                    sh "docker image prune -f || true"
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