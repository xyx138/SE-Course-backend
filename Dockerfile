# 使用 Node 官方镜像作为基础镜像
FROM node:22-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PROJECT_PATH=/app \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_HTTP_TIMEOUT=600 \
    CXXFLAGS="-std=c++11"

# RUN apt-get update && apt-get install -y \
#     python3 \
#     python3-dev \
#     python3-pip \
#     build-essential \
#     gcc \
#     g++ \
#     libffi-dev \
#     curl \
#     && rm -rf /var/lib/apt/lists/*  

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

# 安装 uv (使用官方推荐的安装方法)
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# 运行安装程序并删除它
RUN sh /uv-installer.sh && rm /uv-installer.sh

# 添加 uv 执行路径
ENV PATH="/root/.local/bin/:$PATH"

# 验证 node、npm 和 uv 的版本
RUN node -v && npm -v && uv --version

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY pyproject.toml uv.lock /app/
COPY mcp.json /app/

# 创建必要的目录
RUN mkdir -p /app/knowledge_base \
    /app/VectorStore \
    /app/conversations \
    /app/static \
    /app/practice_history \
    /app/review_plans \
    /app/dist \
    /app/logs \
    /app/node_modules

# 复制项目文件和 .env
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY .envdocker /app/.env
COPY dist/ /app/dist/


# 安装项目
RUN uv python pin 3.11
RUN uv sync

# 暴露应用端口
EXPOSE 8000

# 启动命令
CMD ["uv", "run", "src/api.py"]
