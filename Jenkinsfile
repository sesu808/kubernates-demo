pipeline {
    agent any

    environment {
        AWS_REGION = 'ap-south-1'
        AWS_ACCOUNT_ID = '624858524005'

        ECR_REGISTRY = '624858524005.dkr.ecr.ap-south-1.amazonaws.com'
        ECR_REPO = 'sample-app'

        EKS_CLUSTER = 'sample-eks'
        K8S_NAMESPACE = 'default'
    }

    stages {

        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                dir('app') {
                    sh """
                        docker build -t ${ECR_REPO}:${BUILD_NUMBER} .

                        docker tag ${ECR_REPO}:${BUILD_NUMBER} \
                        ${ECR_REGISTRY}/${ECR_REPO}:${BUILD_NUMBER}

                        docker tag ${ECR_REPO}:${BUILD_NUMBER} \
                        ${ECR_REGISTRY}/${ECR_REPO}:latest
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
                    docker push ${ECR_REGISTRY}/${ECR_REPO}:${BUILD_NUMBER}

                    docker push ${ECR_REGISTRY}/${ECR_REPO}:latest
                """
            }
        }

        stage('Deploy to EKS Cluster') {
            steps {
                sh """
                    aws eks update-kubeconfig \
                    --region ${AWS_REGION} \
                    --name ${EKS_CLUSTER}

                    sed -i "s|IMAGE_URI|${ECR_REGISTRY}/${ECR_REPO}:${BUILD_NUMBER}|g" \
                    k8s/deployment.yaml

                    kubectl apply -f k8s/

                    kubectl rollout status deployment/sample-app \
                    -n ${K8S_NAMESPACE} --timeout=120s
                """
            }
        }

        stage('Verify Kubernetes Deployment') {
            steps {
                sh """
                    echo "Deployments:"
                    kubectl get deployments -n ${K8S_NAMESPACE}

                    echo "\\nPods:"
                    kubectl get pods -n ${K8S_NAMESPACE}

                    echo "\\nServices:"
                    kubectl get svc -n ${K8S_NAMESPACE}

                    echo "\\nIngress:"
                    kubectl get ingress -n ${K8S_NAMESPACE}
                """
            }
        }
    }

    post {

        success {
            echo 'Application deployed successfully to EKS!'
        }

        failure {
            echo 'Pipeline failed!'
        }

        always {
            sh """
                docker rmi ${ECR_REGISTRY}/${ECR_REPO}:${BUILD_NUMBER} || true

                docker rmi ${ECR_REGISTRY}/${ECR_REPO}:latest || true
            """
        }
    }
}
