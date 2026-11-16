pipeline {
    agent {
        label 'test-build'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Test Application') {
            parallel {
                
                //БЭКЕНД
                stage('Test FastAPI (Backend)') {
                    agent {
                        docker { 
                            image 'python:3.11-slim'
                            args '-u root:root'
                        }
                    }
                    steps {
                        sh '''
                            python3 -m venv venv
                            . venv/bin/activate
                            pip install --upgrade pip
                            pip install -r requirements.txt
                            pytest tests/ --junitxml=backend-test-results.xml
                        '''
                    }
                    post {
                        always {
                            junit testResults: '**/backend-test-results.xml', allowEmptyResults: true
                        }
                    }
                }
                
                //ФРОНТ
                stage('Test Vue (Frontend)') {
                    agent {
                        docker { 
                            image 'node:20-alpine'
                            args '-u root:root'
                        }
                    }
                    steps {
                        dir('frontend') {
                            sh '''
                                npm ci
                                npm run lint || echo "Игнорируем ошибки линтера"
                            '''
                        }
                    }
                }
            }
        }

        //СБОРКА ОБРАЗОВ
        stage('Build Docker Images') {
            steps {
                echo "Начинаем сборку. Уникальный номер билда: ${env.BUILD_NUMBER}"
                
                // Сборка бэка
                sh '''
                    docker build -t qvog/webapp-backend:v${BUILD_NUMBER} -t qvog/webapp-backend:latest .
                '''
                
                // Сборка фронта
                sh '''
                    docker build -t qvog/webapp-frontend:v${BUILD_NUMBER} -t qvog/webapp-frontend:latest ./frontend
                '''
            }
        }
    }

    post {
        success {
            echo "OK"
        }
        failure {
            echo "NOT OK"
            // Сохраняем XML-отчеты падающих тестов до того, как workspace будет очищен
            archiveArtifacts artifacts: '**/*.xml', allowEmptyArchive: true
        }
        always {
            cleanWs()
        }
    }
}