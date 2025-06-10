import subprocess
import sys
import time
import signal
import socket
import os
import platform

# 检测操作系统类型
IS_WINDOWS = platform.system() == "Windows"

# Windows 环境下启用 ANSI 颜色支持
if IS_WINDOWS:
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

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
        subprocess.run(['docker', 'info'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
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
        self.container_id = None

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
            # 使用 shell=True 在 Windows 上可能更可靠
            if IS_WINDOWS:
                self.plantuml_process = subprocess.Popen(
                    'docker run -d -p 8080:8080 plantuml/plantuml-server:jetty',
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    text=True
                )
                # 获取容器ID
                self.container_id = self.plantuml_process.stdout.read().strip()
            else:
                self.plantuml_process = subprocess.Popen(
                    ['docker', 'run', '-d', '-p', '8080:8080', 'plantuml/plantuml-server:jetty'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.container_id = self.plantuml_process.stdout.read().decode('utf-8').strip()
        except Exception as e:
            print(f"\033[91mError starting PlantUML server: {e}\033[0m")
            return False

        # 等待PlantUML服务器启动
        print("Waiting for PlantUML server to initialize...")
        time.sleep(5)

        # 启动API服务
        print("\033[92mStarting backend API service...\033[0m")
        try:
            # 使用规范化的路径分隔符
            api_path = os.path.join('src', 'api.py').replace('\\', '/')
            
            if IS_WINDOWS:
                self.api_process = subprocess.Popen(
                    ['uv', 'run', api_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP  # Windows 特定标志
                )
            else:
                self.api_process = subprocess.Popen(
                    ['uv', 'run', api_path],
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
            if IS_WINDOWS:
                # Windows 上优雅地终止进程
                try:
                    self.api_process.terminate()
                    # 给进程一些时间来优雅地关闭
                    for _ in range(10):  # 等待最多1秒
                        if self.api_process.poll() is not None:
                            break
                        time.sleep(0.1)
                    # 如果进程仍在运行，强制终止
                    if self.api_process.poll() is None:
                        self.api_process.kill()
                except Exception as e:
                    print(f"\033[91mError terminating API process: {e}\033[0m")
            else:
                self.api_process.terminate()
                self.api_process.wait()

        # 停止PlantUML服务器
        try:
            if self.container_id:
                subprocess.run(['docker', 'stop', self.container_id], check=True)
            else:
                # 如果没有保存容器ID，尝试通过镜像名查找
                container_id = subprocess.check_output(
                    ['docker', 'ps', '-q', '--filter', 'ancestor=plantuml/plantuml-server:jetty'],
                    text=True
                ).strip()
                if container_id:
                    subprocess.run(['docker', 'stop', container_id], check=True)
        except subprocess.CalledProcessError as e:
            print(f"\033[91mError stopping PlantUML container: {e}\033[0m")
        except Exception as e:
            print(f"\033[91mUnexpected error stopping PlantUML container: {e}\033[0m")

        print("\033[92mAll services stopped\033[0m")

    def monitor_processes(self):
        """监控进程输出"""
        while self.running:
            # 检查API进程输出
            if self.api_process and self.api_process.poll() is None:  # 确保进程仍在运行
                # 非阻塞方式读取输出
                output = self.api_process.stdout.readline()
                if output:
                    try:
                        # Windows 中文环境下优先尝试 GBK 编码
                        if IS_WINDOWS:
                            try:
                                print(output.decode('gbk').strip())
                            except UnicodeDecodeError:
                                print(output.decode('utf-8', errors='replace').strip())
                        else:
                            print(output.decode('utf-8').strip())
                    except UnicodeDecodeError:
                        # 最后的后备方案
                        print(output.decode('latin1', errors='replace').strip())
            else:
                # 如果进程已结束，退出监控
                if self.api_process and self.api_process.poll() is not None:
                    print("\033[91mAPI process has terminated unexpectedly\033[0m")
                    self.running = False
                    break

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
    if not IS_WINDOWS:  # SIGTERM 在 Windows 上不可用
        signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 启动服务
        if manager.start_services():
            print("\033[92mAll services started successfully!\033[0m")
            # 监控进程输出
            manager.monitor_processes()
        else:
            print("\033[91mFailed to start services\033[0m")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\033[93mReceived keyboard interrupt. Shutting down...\033[0m")
    finally:
        manager.cleanup()