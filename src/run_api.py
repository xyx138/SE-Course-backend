#!/usr/bin/env python3
"""
FastAPI应用启动脚本
运行统一的认证和Agent服务
"""

import uvicorn
import os
import sys

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("启动统一认证和Agent服务...")
    print("访问地址: http://localhost:8000")
    print("认证页面: http://localhost:8000/auth")
    print("API文档: http://localhost:8000/docs")
    
    # 启动FastAPI应用
    uvicorn.run(
        "api:app",  # 模块名:应用名
        host="0.0.0.0",
        port=8000,
        reload=False,  # 禁用热重载以避免与Agent线程冲突
        log_level="info"
    ) 