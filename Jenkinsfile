pipeline {
    agent any
    environment {
        AWS_REGION      = 'ap-south-1'
        AWS_ACCOUNT_ID  = '624858524005'
        ECR_REGISTRY    = '624858524005.dkr.ecr.ap-south-1.amazonaws.com'
        ECR_REPO        = 'sample-app'
        EKS_CLUSTER     = 'sample-eks'
        K8S_NAMESPACE   = 'default'
        HELM_RELEASE    = 'sample-app'
        HELM_CHART_PATH = './helm/sample-app'
    }
    stages {
        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }
        stage('Set Version') {
            steps {
                script {
                    def gitTag = sh(
                        script: "git describe --tags --abbrev=0 2>/dev/null || echo 'v0.0.0'",
                        returnStdout: true
                    ).trim()
                    env.IMAGE_TAG = "${gitTag}-${BUILD_NUMBER}"
                    echo "Deploying version: ${env.IMAGE_TAG}"
                }
            }
        }
        stage('Build Docker Image') {
            steps {
                dir('app') {
                    sh """
                        docker build -t ${ECR_REPO}:${IMAGE_TAG} .
                        docker tag ${ECR_REPO}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
                    """
                }
            }
        }
        stage('Login to Amazon ECR') {
            steps {
                sh """
                    aws ecr get-login-password --region ${AWS_REGION} | \
                    docker login --username AWS --password-stdin ${ECR_REGISTRY}
                """
            }
        }
        stage('Push Docker Image to ECR') {
            steps {
                sh """
                    docker push ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
                """
            }
        }
        stage('Deploy to EKS via Helm') {
            steps {
                sh """
                    aws eks update-kubeconfig \
                        --region ${AWS_REGION} \
                        --name ${EKS_CLUSTER}

                    helm upgrade --install ${HELM_RELEASE} ${HELM_CHART_PATH} \
                        --namespace ${K8S_NAMESPACE} \
                        --create-namespace \
                        --set image.repository=${ECR_REGISTRY}/${ECR_REPO} \
                        --set image.tag=${IMAGE_TAG} \
                        --set image.pullPolicy=IfNotPresent \
                        --wait \
                        --timeout 2m \
                        --atomic
                """
            }
        }
        stage('Verify Deployment') {
            steps {
                sh """
                    echo "==> Deployed Version: ${IMAGE_TAG}"
                    helm status ${HELM_RELEASE} -n ${K8S_NAMESPACE}
                    helm history ${HELM_RELEASE} -n ${K8S_NAMESPACE}
                    kubectl get pods -n ${K8S_NAMESPACE}
                    kubectl get svc -n ${K8S_NAMESPACE}
                """
            }
        }
    }
    post {
        success {
            echo "Successfully deployed version: ${IMAGE_TAG}"
        }
        failure {
            echo "Deployment failed! Rolling back..."
            sh "helm rollback ${HELM_RELEASE} 0 -n ${K8S_NAMESPACE} || true"
        }
        always {
            sh """
                docker rmi ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG} || true
                docker rmi ${ECR_REPO}:${IMAGE_TAG} || true
            """
        }
    }
}