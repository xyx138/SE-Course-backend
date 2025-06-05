# 统一认证和Agent服务系统

这是一个集成了学生/管理员认证系统和AI Agent服务的统一平台。

## 功能特性

### 认证系统
- 🏫 学生注册和登录
- 👨‍💼 管理员注册和登录
- 🔐 密码加密存储（使用Werkzeug）
- 💾 SQLite数据库存储用户信息
- 🎨 现代化的统一认证界面

### Agent服务
- 💬 智能对话Agent
- 📊 UML图生成服务
- 📚 概念解释服务
- 📝 智能题目生成和批改
- 📄 论文搜索和分析服务

## 项目结构

```
src/
├── api.py                 # FastAPI主应用（包含所有API接口）
├── app.py                 # 原Flask应用（已整合到api.py）
├── database.py            # 数据库操作模块
├── run_api.py            # 启动脚本
├── templates/
│   ├── unified_auth.html  # 统一认证页面
│   ├── student_dashboard.html   # 学生仪表板
│   └── admin_dashboard.html     # 管理员仪表板
└── agents/               # AI Agent模块
    ├── agent.py
    ├── umlAgent.py
    ├── explainAgent.py
    ├── questionAgent.py
    └── paperAgent.py
data/
└── auth.db              # SQLite数据库文件（自动创建）
requirements.txt         # 项目依赖
```

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件并设置必要的环境变量：

```env
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_BASE_URL=your_base_url_here
PROJECT_PATH=/path/to/your/project
```

### 3. 启动服务

```bash
cd src
python run_api.py
```

或者直接运行：

```bash
cd src
python api.py
```

### 4. 访问服务

- **主页/认证页面**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **学生仪表板**: http://localhost:8000/student/dashboard
- **管理员仪表板**: http://localhost:8000/admin/dashboard

## API接口

### 认证相关接口

#### 学生接口
- `POST /api/student/login` - 学生登录
- `POST /api/student/register` - 学生注册

#### 管理员接口
- `POST /api/admin/login` - 管理员登录
- `POST /api/admin/register` - 管理员注册

### Agent服务接口

#### 基础对话
- `POST /chat` - 与AI Agent对话

#### 知识库管理
- `POST /create_or_update_index` - 创建/更新知识库
- `GET /list_knowledge_bases` - 获取知识库列表
- `POST /delete_knowledge_base` - 删除知识库
- `POST /update_label` - 更新知识库标签

#### UML图生成
- `POST /umlAgent/generate_uml` - 生成UML图

#### 概念解释
- `POST /explainAgent/explain` - 生成概念解释

#### 题目相关
- `POST /questionAgent/explain_question` - 解释题目
- `POST /questionAgent/generate_practice_set` - 生成练习题
- `POST /questionAgent/grade_practice_set` - 批改练习题

#### 论文服务
- `POST /paperAgent/search_papers` - 搜索论文
- `POST /paperAgent/download_and_read_paper` - 下载并阅读论文
- `POST /paperAgent/list_and_organize_papers` - 列出并组织论文
- `POST /paperAgent/analyze_paper_for_project` - 分析论文应用价值
- `POST /paperAgent/recommend_learning_path` - 推荐学习路径

## 数据库结构

### 学生表 (students)
- `id` - 主键
- `student_id` - 学号（唯一）
- `password` - 加密密码
- `name` - 姓名
- `created_at` - 创建时间

### 管理员表 (administrators)
- `id` - 主键
- `manager_id` - 管理员ID（唯一）
- `password` - 加密密码
- `name` - 姓名
- `created_at` - 创建时间

## 使用说明

1. **首次使用**: 访问主页后选择"学生"或"管理员"标签进行注册
2. **登录**: 注册成功后可以使用相同的标签页进行登录
3. **仪表板**: 登录成功后会跳转到相应的仪表板页面
4. **Agent服务**: 可以通过API接口调用各种AI服务

## 技术栈

- **后端**: FastAPI + Python 3.8+
- **数据库**: SQLite 3
- **前端**: HTML + CSS + JavaScript
- **密码加密**: Werkzeug
- **AI服务**: 通义千问API

## 注意事项

1. 首次运行时会自动创建数据库文件
2. Agent服务需要配置正确的API密钥才能正常工作
3. 系统默认运行在8000端口，请确保端口未被占用
4. 生产环境部署时建议修改secret_key和数据库配置

## 开发和调试

- 查看API文档: http://localhost:8000/docs
- 查看交互式API: http://localhost:8000/redoc
- 日志级别可在启动脚本中调整

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

