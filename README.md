# 软件工程课设 - 智能助手系统

## ✨ 功能特点

- **🤔 智能问答**：基于知识库内容回答用户问题，使用检索增强生成（RAG）技术
- **🛠️ 工具调用**：通过MCP协议使用外部工具执行任务
- **📋 知识管理**：支持创建、更新和删除知识库
- **📊 UML图生成**：根据文字描述自动生成各类UML图
- **📝 概念解释**：提供多种风格的概念解释和学习资料
- **✏️ 题目解答**：解答软件工程相关题目并提供详细解析
- **📄 论文助手**：搜索、下载、分析学术论文，并提供学习路径

## 🛠️ 已实现的智能体

- **Agent**：通用对话智能体，支持知识库检索和工具调用
- **UML_Agent**：UML图生成智能体，支持类图、序列图等多种图表生成
- **ExplainAgent**：概念解释智能体，支持多种解释风格
- **QuestionAgent**：题目解答智能体，支持题目解析和练习题生成
- **PaperAgent**：论文助手智能体，支持论文搜索、阅读和分析

## 🔌 已接入的工具

- **Filesystem**：文件系统操作工具
- **Fetch**：网络请求工具
- **PlantUML**：UML图表生成服务
- **Arxiv-MCP**：学术论文搜索和下载服务
- **time**: 获取时间
- **memory**: 基于对话内容构建知识图谱
- **bingcn**: bing搜索

## 🚀 使用方法

### 🔍 环境要求

- Python 3.10+
- Node.js 16+
- Docker

### ▶️ 启动服务

1. 克隆项目并进入项目

   ```bash
   git clone git@github.com:xyx138/SE-Course-backend.git
   cd SE-Course-backend
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

4. 安装 Node.js（以Windows为例，如果已安装可跳过此步）

   访问[Node.js官网](https://nodejs.org/en)，选择下载msi文件，点击msi文件后一路下一步即可

   ```bash
   # 验证是否安装成功
   node -v # v16+ 
   npm -v # 8+
   ```

5. Docker相关设置
   1. [安装Docker](https://www.docker.com/)
   2. 进入终端，执行下列命令
      ```bash
      docker pull plantuml/plantuml-server:jetty
      ```

6. 修改配置文件

   复制`.env.example`并重命名为`.env`, 完善`.env`的内容

   [千问API权限获取和创建](https://help.aliyun.com/zh/model-studio/get-api-key?spm=a2c4g.11186623.0.0.374f6401cARvVK)

7. 启动项目

   ```bash
   # 启动PlantUML服务器（用于UML图生成）
   docker run -d -p 8080:8080 plantuml/plantuml-server:jetty
   
   # 启动后端API服务
   uv run src/api.py
   
   # 启动前端Gradio界面（在另一个终端窗口）
   uv run src/main.py
   ```

8. 访问系统

   在浏览器中打开 [http://localhost:7860](http://localhost:7860) 访问前端界面

## 💡 系统架构

本系统采用前后端分离架构：
- 后端：FastAPI 提供 RESTful API
- 前端：暂时使用 Gradio 构建用户界面
- 通信：通过 HTTP 请求进行前后端交互
- 工具调用：使用 MCP (Model Context Protocol) 协议

## 📚 参考文献

- [Anthropic MCP 协议文档](https://docs.anthropic.com/zh-CN/docs/agents-and-tools/mcp)
- [检索增强生成 (RAG) 概述](https://scriv.ai/guides/retrieval-augmented-generation-overview/)
- [OpenAI API 参考文档](https://platform.openai.com/docs/api-reference/responses)

