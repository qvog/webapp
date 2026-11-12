pipeline {
    agent any // Пока запускаем прямо внутри контейнера Jenkins

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo "Код скачан. Текущая ветка: ${env.BRANCH_NAME}"
            }
        }
        
        stage('Test Application') {
            parallel {
                // ВЕТКА 1: БЭКЕНД
                stage('Test FastAPI (Backend)') {
                    steps {
                        // Если бэкенд в папке backend, раскомментируй dir:
                        // dir('backend') {
                        sh '''
                            echo "--- Инициализация бэкенда ---"
                            python3 -m venv venv
                            . venv/bin/activate
                            pip install --upgrade pip
                            pip install -r requirements.txt
                            # Запускаем тесты и генерируем отчет
                            pytest tests/ --junitxml=backend-test-results.xml
                        '''
                        // }
                    }
                    post {
                        always {
                            // Собираем XML отчет о тестах, даже если они упали
                            junit '**/backend-test-results.xml'
                        }
                    }
                }
                
                // ВЕТКА 2: ФРОНТЕНД
                stage('Test Vue (Frontend)') {
                    steps {
                        // Если фронтенд в папке frontend, раскомментируй dir:
                        // dir('frontend') {
                        sh '''
                            echo "--- Поднимаем фронтенд ---"
                            # Чистая установка зависимостей для CI
                            npm ci
                            # Запуск линтера (проверка качества кода)
                            npm run lint || echo "Линтер ругается, но идем дальше"
                        '''
                        // }
                    }
                }
            }
        }

        stage('Build Docker Images') {
            steps {
                echo "Заглушка для сборки Docker..."
            }
        }
    }

    post {
        always {
            cleanWs()
            echo "Рабочая директория очищена."
        }
    }
}