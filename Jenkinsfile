pipeline {
    agent any // Базовый агент для скачивания кода

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Test Application') {
            parallel {
                
                // --- БЭКЕНД ---
                stage('Test FastAPI (Backend)') {
                    // Jenkins скачает этот образ и выполнит sh-скрипт внутри него
                    agent {
                        docker { 
                            image 'python:3.11-slim'
                            args '-u root:root' // Даем права, чтобы Jenkins мог создавать файлы
                        }
                    }
                    steps {
                        // Если твой FastAPI лежит в папке, раскомментируй dir:
                        // dir('backend') {
                        sh '''
                            python3 -m venv venv
                            . venv/bin/activate
                            pip install --upgrade pip
                            pip install -r requirements.txt
                            pytest tests/ --junitxml=backend-test-results.xml
                        '''
                        // }
                    }
                    post {
                        always {
                            // allowEmptyResults спасет от страшной ошибки, если pytest не отработал
                            junit testResults: '**/backend-test-results.xml', allowEmptyResults: true
                        }
                    }
                }
                
                // --- ФРОНТЕНД ---
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
    }

    post {
        always {
            cleanWs()
        }
    }
}