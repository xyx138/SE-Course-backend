#!/usr/bin/env python3
"""
启动脚本 - 激活虚拟环境并同时运行api.py和main.py (使用Python直接运行)
"""

import os
import sys
import subprocess
import time
import signal
import atexit
import platform

# 存储进程对象
processes = []

def start_services():
    """
    启动API服务和Gradio界面
    """
    print("=" * 50)
    print("启动知识库智能问答系统")
    print("=" * 50)

    # 确保当前工作目录正确
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir) if script_dir.endswith('scripts') else script_dir
    os.chdir(project_root)
    
    # 确定虚拟环境中的Python解释器路径
    is_windows = platform.system() == "Windows"
    
    if is_windows:
        python_path = os.path.join(project_root, ".venv", "Scripts", "python.exe")
    else:
        python_path = os.path.join(project_root, ".venv", "bin", "python")
    
    # 检查Python解释器是否存在
    if not os.path.exists(python_path):
        print(f"错误: 虚拟环境Python解释器未找到: {python_path}")
        print("请确保虚拟环境已正确创建并位于项目根目录的.venv文件夹中")
        sys.exit(1)
    
    # 启动API服务
    print("\n[1/2] 正在启动后端API服务...")
    api_script = os.path.join(project_root, "src", "api.py")
    
    # 直接使用虚拟环境中的Python解释器启动脚本
    api_process = subprocess.Popen(
        [python_path, api_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(api_process)
    print(f"API服务启动成功 (PID: {api_process.pid})")
    
    # 等待API服务启动
    print("等待API服务完全启动 (3秒)...")
    time.sleep(3)
    
    # 启动Gradio界面
    print("\n[2/2] 正在启动Gradio前端界面...")
    main_script = os.path.join(project_root, "src", "main.py")
    
    # 直接使用虚拟环境中的Python解释器启动脚本
    ui_process = subprocess.Popen(
        [python_path, main_script],
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(ui_process)
    print(f"Gradio界面启动成功 (PID: {ui_process.pid})")
    
    return api_process, ui_process

def cleanup():
    """
    清理进程
    """
    print("\n" + "=" * 50)
    print("正在关闭所有服务...")
    
    for process in processes:
        if process.poll() is None:  # 如果进程仍在运行
            try:
                process.terminate()  # 尝试优雅终止
                process.wait(timeout=3)  # 等待进程终止
            except subprocess.TimeoutExpired:
                process.kill()  # 如果超时，强制终止
                print(f"已强制关闭进程 (PID: {process.pid})")
            else:
                print(f"已优雅关闭进程 (PID: {process.pid})")
    
    print("所有服务已关闭")
    print("=" * 50)

def signal_handler(sig, frame):
    """
    处理中断信号
    """
    print("\n检测到中断信号，开始关闭服务...")
    cleanup()
    sys.exit(0)

def monitor_processes(api_process, ui_process):
    """
    监控进程输出并检查是否终止
    """
    print("\n" + "=" * 50)
    print("系统已启动 - 按Ctrl+C可关闭所有服务")
    print("=" * 50 + "\n")
    
    try:
        while True:
            # 检查API进程是否终止
            api_returncode = api_process.poll()
            if api_returncode is not None:
                print(f"错误: API服务意外终止 (返回码: {api_returncode})")
                # 输出最后的错误信息
                output, _ = api_process.communicate()
                if output:
                    print(f"API服务最后输出:\n{output}")
                break
                
            # 检查UI进程是否终止
            ui_returncode = ui_process.poll()
            if ui_returncode is not None:
                print(f"错误: Gradio界面意外终止 (返回码: {ui_returncode})")
                # 输出最后的错误信息
                output, _ = ui_process.communicate()
                if output:
                    print(f"Gradio界面最后输出:\n{output}")
                break
                
            # 读取并显示输出
            for process, name in [(api_process, "API"), (ui_process, "UI")]:
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    print(f"[{name}] {line.strip()}")
            
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n检测到Ctrl+C，正在关闭服务...")
    finally:
        cleanup()

if __name__ == "__main__":
    # 注册退出和信号处理函数
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动服务
    api_process, ui_process = start_services()
    
    # 监控服务
    monitor_processes(api_process, ui_process)
