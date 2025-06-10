#!/bin/bash

# 设置颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting services...${NC}"


# 检查端口8080是否被占用
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${RED}Port 8080 is already in use. Please free up the port first.${NC}"
    exit 1
fi

# 启动PlantUML服务器
echo "Starting PlantUML server..."
docker run -d -p 8080:8080 plantuml/plantuml-server:jetty


# 等待几秒确保PlantUML服务器完全启动
echo "Waiting for PlantUML server to initialize..."

# 启动后端API服务
echo "Starting backend API service..."
uv run src/api.py

# 捕获Ctrl+C信号
trap 'cleanup' INT

# 清理函数
cleanup() {
    echo -e "\n${GREEN}Stopping services...${NC}"
    # 停止PlantUML服务器
    docker stop $(docker ps -q --filter ancestor=plantuml/plantuml-server:jetty)
    echo -e "${GREEN}Services stopped${NC}"
    exit 0
}
