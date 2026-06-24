import subprocess
import sys
import os
import time

def main():
    print("🚀 [СИСТЕМА] Запуск HFT-Терминала (Режим Разработки)...")

    # Определяем абсолютные пути
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(base_dir, "frontend")

    # Команда для npm (учитываем разницу между Windows и Linux/WSL)
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"

    # 1. Запускаем Backend (FastAPI) в фоне
    print("🐍 Запуск Python Backend (Порт 8000)...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"]
    )

    # Даем бэкенду секунду на старт, чтобы фронтенд не стучался в пустоту
    time.sleep(1)

    # 2. Запускаем Frontend (Vue/Vite) в фоне
    print("⚡ Запуск Vue Frontend (Порт 5173)...")
    frontend_process = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=frontend_dir # Указываем, что эту команду нужно выполнить в папке frontend-vue
    )

    try:
        # Бесконечный цикл, чтобы скрипт run.py не завершился сам по себе
        while True:
            time.sleep(1)
            
            # Если какой-то из серверов упал с ошибкой, тушим всё
            if backend_process.poll() is not None or frontend_process.poll() is not None:
                print("⚠️ Один из серверов неожиданно завершил работу.")
                break
                
    except KeyboardInterrupt:
        # Срабатывает, когда вы нажимаете Ctrl+C в консоли
        print("\n🛑 Получен сигнал остановки (Ctrl+C). Тушим серверы...")
        
    finally:
        # Аккуратно завершаем оба процесса, чтобы освободить порты 8000 и 5173
        if backend_process.poll() is None:
            backend_process.terminate()
            backend_process.wait()
            print("✅ Backend остановлен.")
            
        if frontend_process.poll() is None:
            frontend_process.terminate()
            frontend_process.wait()
            print("✅ Frontend остановлен.")
            
        print("🏁 Работа терминала полностью завершена.")

if __name__ == "__main__":
    main()