# 🤖 Agent = LLM + MCP + RAG

## 📝 项目简介

这是一个结合大语言模型(LLM)、模型上下文协议(MCP)和检索增强生成(RAG)技术的智能Agent系统。该系统可以通过检索知识库的相关信息，借助大语言模型的理解和推理能力，并通过工具调用执行实际操作，提供智能化的问答和任务执行功能。

## 🧩 核心组件

### 1. 🧠 大语言模型 (LLM)

- 基于OpenAI兼容接口的LLM客户端
- 支持通义千问等大模型
- 负责自然语言理解、推理和回答生成

### 2. 🔧 模型上下文协议 (MCP)

- 基于MCP协议的工具调用框架
- 支持动态加载和使用多种工具
- 提供文件操作、地图查询等工具能力

### 3. 📚 检索增强生成 (RAG)

- 基于向量数据库的知识检索系统
- 支持创建和管理多个知识库
- 利用语义检索技术找到最相关的信息

## 🏗️ 系统架构

```
┌───────────────────┐
│     用户界面      │
│  (Gradio WebUI)   │
└─────────┬─────────┘
          │
┌─────────▼─────────┐
│    API服务       │
│  (FastAPI)       │
└─────────┬─────────┘
          │
┌─────────▼─────────┐
│    Agent 核心     │
└─────────┬─────────┘
          │
┌─────────┴─────────┐
│                   │
▼                   ▼
┌───────────┐  ┌────────────┐  ┌────────────┐
│    LLM    │  │    MCP     │  │    RAG     │
│  客户端   │  │  工具客户端 │  │ 检索系统   │
└───────────┘  └────────────┘  └────────────┘
```

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
   git clone git@github.com:xyx138/agent-llm-mcp-rag.git
   cd agent-llm-mcp-rag
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

5. 修改配置文件

   复制`.env.example`到同级目录下，并更名为`.env`, 将其中的**api和项目路径**改为自己的，创建api可以参考下面的文档

   ![image-20250506143814101](https://raw.githubusercontent.com/xyx138/cloudimg/master/img/image-20250506143814101.png)

   [高德地图api权限获取和创建](https://amap.apifox.cn/doc-537183)

   [千问api权限获取和创建](https://help.aliyun.com/zh/model-studio/get-api-key?spm=a2c4g.11186623.0.0.374f6401cARvVK)

6. 启动项目

```bash
uv run src/api.py
```

