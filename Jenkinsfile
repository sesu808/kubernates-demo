pipeline {
    agent any

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

        INGRESS_ENABLED       = 'true'
        INGRESS_CLASS         = 'alb'

        // Autoscaling
        HPA_ENABLED           = 'true'
        HPA_MIN_REPLICAS      = '2'
        HPA_MAX_REPLICAS      = '5'
        HPA_CPU_TARGET        = '70'
        HPA_MEMORY_TARGET     = '80'
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
                        # Chart metadata
                        sed -i 's/^version:.*/version: ${CHART_VERSION}/'       ${HELM_CHART_PATH}/Chart.yaml
                        sed -i 's/^appVersion:.*/appVersion: "${IMAGE_TAG}"/'   ${HELM_CHART_PATH}/Chart.yaml

                        # Image
                        sed -i 's|repository:.*|repository: ${ECR_IMAGE}|'      ${HELM_CHART_PATH}/values.yaml
                        sed -i 's|tag:.*|tag: "${IMAGE_TAG}"|'                  ${HELM_CHART_PATH}/values.yaml

                        # Ingress
                        sed -i 's|^  enabled:.*|  enabled: ${INGRESS_ENABLED}|' ${HELM_CHART_PATH}/values.yaml

                        # Autoscaling
                        sed -i 's|^  minReplicas:.*|  minReplicas: ${HPA_MIN_REPLICAS}|'                               ${HELM_CHART_PATH}/values.yaml
                        sed -i 's|^  maxReplicas:.*|  maxReplicas: ${HPA_MAX_REPLICAS}|'                               ${HELM_CHART_PATH}/values.yaml
                        sed -i 's|^  targetCPUUtilizationPercentage:.*|  targetCPUUtilizationPercentage: ${HPA_CPU_TARGET}|'       ${HELM_CHART_PATH}/values.yaml
                        sed -i 's|^  targetMemoryUtilizationPercentage:.*|  targetMemoryUtilizationPercentage: ${HPA_MEMORY_TARGET}|' ${HELM_CHART_PATH}/values.yaml
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
                expression { env.IMAGE_TAG != null }
            }
            steps {
                sh """
                    helm upgrade --install kubernates-demo ${HELM_CHART_PATH} \
                        --namespace production \
                        --create-namespace \
                        --set image.repository=${ECR_IMAGE} \
                        --set image.tag=${IMAGE_TAG} \
                        --set ingress.enabled=true \
                        --set ingress.className=alb \
                        --set "ingress.annotations.kubernetes\\.io/ingress\\.class=alb" \
                        --set "ingress.annotations.alb\\.ingress\\.kubernetes\\.io/scheme=internet-facing" \
                        --set "ingress.annotations.alb\\.ingress\\.kubernetes\\.io/target-type=ip" \
                        --set httpRoute.enabled=false \
                        --set autoscaling.enabled=${HPA_ENABLED} \
                        --set autoscaling.minReplicas=${HPA_MIN_REPLICAS} \
                        --set autoscaling.maxReplicas=${HPA_MAX_REPLICAS} \
                        --set autoscaling.targetCPUUtilizationPercentage=${HPA_CPU_TARGET} \
                        --set autoscaling.targetMemoryUtilizationPercentage=${HPA_MEMORY_TARGET}
                """
            }
        }

    }   // end stages

    post {
        success {
            echo "✅ Successfully built, pushed to ECR, and deployed Helm chart ${env.IMAGE_TAG} with autoscaling (${HPA_MIN_REPLICAS}-${HPA_MAX_REPLICAS} replicas)"
        }
        failure {
            echo "❌ Pipeline failed. Check console output above."
        }
        always {
            sh "docker rmi ${ECR_IMAGE}:${IMAGE_TAG} || true"
            cleanWs()
        }
    }

}   // end pipeline