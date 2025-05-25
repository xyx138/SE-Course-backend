import subprocess
import sys
import time
import signal
import socket
import os

def check_port(port):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('', port))
            return False
        except socket.error:
            return True

def is_docker_running():
    """检查Docker是否正在运行"""
    try:
        subprocess.run(['docker', 'info'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False

class ServiceManager:
    def __init__(self):
        self.plantuml_process = None
        self.api_process = None
        self.running = True

    def start_services(self):
        """启动所有服务"""
        # 检查Docker是否运行
        if not is_docker_running():
            print("\033[91mError: Docker is not running. Please start Docker first.\033[0m")
            return False

        # 检查端口
        if check_port(8080):
            print("\033[91mError: Port 8080 is already in use. Please free up the port first.\033[0m")
            return False

        # 启动PlantUML服务器
        print("\033[92mStarting PlantUML server...\033[0m")
        try:
            self.plantuml_process = subprocess.Popen(
                ['docker', 'run', '-d', '-p', '8080:8080', 'plantuml/plantuml-server:jetty'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            print(f"\033[91mError starting PlantUML server: {e}\033[0m")
            return False

        # 等待PlantUML服务器启动
        print("Waiting for PlantUML server to initialize...")
        time.sleep(5)

        # 启动API服务
        print("\033[92mStarting backend API service...\033[0m")
        try:
            self.api_process = subprocess.Popen(
                ['uv', 'run', 'src/api.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            print(f"\033[91mError starting API service: {e}\033[0m")
            self.cleanup()
            return False
        except FileNotFoundError:
            print("\033[91mError: 'uv' command not found. Please install uv first.\033[0m")
            self.cleanup()
            return False

        return True

    def cleanup(self):
        """清理所有服务"""
        print("\n\033[93mStopping services...\033[0m")

        # 停止API服务
        if self.api_process:
            self.api_process.terminate()
            self.api_process.wait()

        # 停止PlantUML服务器
        if self.plantuml_process:
            try:
                container_id = subprocess.check_output(
                    ['docker', 'ps', '-q', '--filter', 'ancestor=plantuml/plantuml-server:jetty'],
                    text=True
                ).strip()
                if container_id:
                    subprocess.run(['docker', 'stop', container_id], check=True)
            except subprocess.CalledProcessError as e:
                print(f"\033[91mError stopping PlantUML container: {e}\033[0m")

        print("\033[92mAll services stopped\033[0m")

    def monitor_processes(self):
        """监控进程输出"""
        while self.running:
            # 检查API进程输出
            if self.api_process:
                output = self.api_process.stdout.readline()
                if output:
                    print(output.decode().strip())

            # 简单的延时，避免CPU过度使用
            time.sleep(0.1)

def signal_handler(signum, frame):
    """信号处理函数"""
    print("\n\033[93mReceived shutdown signal. Cleaning up...\033[0m")
    manager.running = False
    manager.cleanup()
    sys.exit(0)

if __name__ == "__main__":
    # 创建服务管理器
    manager = ServiceManager()

    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 启动服务
        if manager.start_services():
            # print("\033[92mAll services started successfully!\033[0m")
            # 监控进程输出
            manager.monitor_processes()
        else:
            print("\033[91mFailed to start services\033[0m")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\033[93mReceived keyboard interrupt. Shutting down...\033[0m")
    finally:
        manager.cleanup()