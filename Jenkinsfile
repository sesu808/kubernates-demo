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
                            helm history kubernates-demo -n production \
                                --output json 2>/dev/null | \
                            python3 -c \"
import sys, json
history = json.load(sys.stdin)
successful = [h for h in history if h['status'] in ['deployed', 'superseded']]
print(successful[-1]['revision'] if successful else '0')
\" 2>/dev/null || echo '0'
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
                                --set ingress.enabled=false \
                                --set httpRoute.enabled=false \
                                --set autoscaling.enabled=false \
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

                            slackSend(
                                channel: 'C0B6VQ7Q9NH',
                                color: 'warning',
                                message: """⚠️ *Rollback Triggered*
*Job:* ${env.JOB_NAME}
*Build:* #${env.BUILD_NUMBER}
*Failed Version:* ${env.IMAGE_TAG}
*Rolled Back To Revision:* ${env.HELM_REVISION}
*URL:* ${env.BUILD_URL}"""
                            )
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
            slackSend(
                channel: 'C0B6VQ7Q9NH',
                color: 'good',
                message: """✅ *Deployment Successful*
*Job:* ${env.JOB_NAME}
*Build:* #${env.BUILD_NUMBER}
*Version:* ${env.IMAGE_TAG}
*Duration:* ${currentBuild.durationString}
*URL:* ${env.BUILD_URL}"""
            )
        }
        failure {
            echo "❌ Pipeline failed."
            slackSend(
                channel: 'C0B6VQ7Q9NH',
                color: 'danger',
                message: """❌ *Pipeline Failed*
*Job:* ${env.JOB_NAME}
*Build:* #${env.BUILD_NUMBER}
*Version:* ${env.IMAGE_TAG ?: 'N/A'}
*Duration:* ${currentBuild.durationString}
*URL:* ${env.BUILD_URL}"""
            )
        }
        aborted {
            echo "⚠️ Deployment rejected at approval."
            slackSend(
                channel: 'C0B6VQ7Q9NH',
                color: 'warning',
                message: """⚠️ *Deployment Aborted*
*Job:* ${env.JOB_NAME}
*Build:* #${env.BUILD_NUMBER}
*Version:* ${env.IMAGE_TAG ?: 'N/A'}
*Reason:* Rejected at approval stage"""
            )
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