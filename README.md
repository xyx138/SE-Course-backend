## ✨ 功能特点

- **🤔 智能问答**：基于知识库内容回答用户问题
- **🛠️ 工具调用**：通过MCP协议使用外部工具执行任务
    >目前只接入了fetch、filesystem、高德地图
- **📋 知识管理**：支持创建、更新和删除知识库
- **🔄 灵活扩展**：易于添加新的工具和功能

## 🚀 使用方法

### 🔍 环境要求

- Python 3.10+

### ▶️ 启动服务

1. 克隆项目并进入项目

   ```bash
   git clone git@github.com:xyx138/SE-Course-backend.git
   cd SE-Course-backen
   ```

2. 安装 uv

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh  # linux/mac
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"  # windows
   ```

   重启终端，确保 uv 命令生效

3. 进入项目根目录，创建虚拟环境

   ```bash
   uv python pin 3.11 # 指定python版本
   uv sync # 创建环境并同步依赖
   ```

4. 安装 node （以windows为例，如果安装过node跳过这步）

   访问[node官网](https://nodejs.org/en)，选择下载msi文件，点击msi文件后一路下一步即可

   ```bash
   # 验证是否安装成功
   node -v # v22.15.0
   npm -v # 10.9.2
   ```

5. docker相关
   1. [安装docker](https://www.docker.com/)
   2. 进入终端，执行下列命令
      ```bash
      docker pull plantuml/plantuml-server:jetty
      ```


6. 修改配置文件

   复制`.env.example`并重命名为`.env`, 完善`.env`的内容

   [千问api权限获取和创建](https://help.aliyun.com/zh/model-studio/get-api-key?spm=a2c4g.11186623.0.0.374f6401cARvVK)

7. 启动项目

   ```bash
   docker run -d -p 8080:8080 plantuml/plantuml-server:jetty # 启动docker容器
   uv run src/api.py # 启动后端服务
   ```

## 📚 参考文献

- [Anthropic MCP 协议文档](https://docs.anthropic.com/zh-CN/docs/agents-and-tools/mcp)
- [检索增强生成 (RAG) 概述](https://scriv.ai/guides/retrieval-augmented-generation-overview/)
- [OpenAI API 参考文档](https://platform.openai.com/docs/api-reference/responses)

