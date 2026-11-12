pipeline {
    agent any // Пока используем локальную среду агента

    stages {
        stage('Checkout') {
            steps {
                // Jenkins сам скачает нужную ветку
                checkout scm
                echo "Код скачан. Текущая ветка: ${env.BRANCH_NAME}"
            }
        }
        
        // Вот она, магия параллельного выполнения!
        stage('Test Application') {
            parallel {
                stage('Test FastAPI (Backend)') {
                    steps {
                        echo "Тут будет: python -m venv, pip install и запуск pytest"
                    }
                }
                stage('Test Vue (Frontend)') {
                    steps {
                        echo "Тут будет: npm ci, lint и запуск фронтовых тестов"
                    }
                }
            }
        }

        stage('Build Docker Images') {
            steps {
                echo "Тут будет docker build для фронта и бэка..."
            }
        }
    }

    // Блок гигиены
    post {
        always {
            cleanWs()
            echo "Рабочая директория очищена, мусора на диске не осталось."
        }
    }
}