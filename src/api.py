'''
 -----------------------------------------------------------------------------
 双线程架构说明
 -----------------------------------------------------------------------------

 本API服务采用双线程架构设计，包含两个主要线程：

 1. 主线程 (FastAPI/uvicorn线程)
    - 职责：处理HTTP请求，运行FastAPI端点函数
    - 创建方式：uvicorn.run(app)自动创建
    - 特点：有自己的事件循环，用于处理异步HTTP请求
    - 注意事项：不应直接调用Agent的异步方法，应使用线程安全通信机制

 2. Agent线程 (后台线程)
    - 职责：初始化和运行Agent，处理所有工具调用
    - 创建方式：threading.Thread(target=background_start_agent)
    - 特点：创建独立事件循环(agent_loop)，维护Agent和MCP客户端生命周期
    - 注意事项：所有Agent异步操作必须在此线程的事件循环中执行

 线程间通信方式：
 - 使用concurrent.futures.Future实现线程间结果传递
 - 使用agent_loop.call_soon_threadsafe在Agent线程中安排任务执行
 - 全局变量agent和agent_loop用于共享对象引用

 为何使用双线程架构：
 1. 防止跨线程边界问题：异步对象必须在创建它们的同一事件循环中使用
 2. 实现资源隔离：API请求处理与Agent操作分离，提高稳定性
 3. 保持MCP客户端连接：Agent线程持续运行，维护工具连接状态
 4. 允许并发处理：同时处理多个API请求而不阻塞Agent工作

 典型使用模式（参见chat端点实现）：
 1. 在API端点中创建Future对象
 2. 使用call_soon_threadsafe在Agent线程中安排函数执行
 3. 在安排的函数中创建协程并用agent_loop.create_task执行
 4. 通过回调将结果设置到Future对象
 5. API线程使用run_in_executor等待Future结果

 -----------------------------------------------------------------------------
'''
 

from agent import Agent
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from dotenv import load_dotenv
import threading
import os
from pydantic import BaseModel
import asyncio
import uvicorn
import time
from typing import List, Optional
import shutil
import concurrent.futures
import functools
from fastapi.middleware.cors import CORSMiddleware
from requirements_agent import RequirementsAnalysis
import base64

from pydantic import BaseModel
from llmClient import LLMClient
from dotenv import load_dotenv
from requirements_agent import Requirement
from typing import Dict
import json
from typing import Dict
load_dotenv()
api_key = os.getenv("DASHSCOPE_API_KEY")
base_url = os.getenv("DASHSCOPE_BASE_URL")
model = 'qwen-plus'

# 确保必要的目录存在
KNOWLEDGE_DIR = os.path.join(os.getenv("PROJECT_PATH"), "knowledge_base")
VECTOR_STORE_DIR = os.path.join(os.getenv("PROJECT_PATH"), "VectorStore")

PROJECT_ROOT = os.getenv("PROJECT_PATH")


load_dotenv()

class Requirement(BaseModel):
    """需求模型"""
    id: str
    type: str  # 功能需求/非功能需求
    category: str  # 具体类别
    description: str
    priority: str  # 高/中/低
    dependencies: List[str] = []
    acceptance_criteria: List[str] = []

class RequirementsAnalysis:
    """需求分析智能体"""
    def __init__(self):
        # 从环境变量获取配置
        api_key = os.getenv("DASHSCOPE_API_KEY")
        base_url = os.getenv("DASHSCOPE_BASE_URL")
        model = os.getenv("DASHSCOPE_MODEL", "qwen-plus")
        
        if not all([api_key, base_url, model]):
            raise ValueError("缺少必要的环境变量配置：DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, DASHSCOPE_MODEL")
            
        self.llm_client = LLMClient(api_key, base_url, model)
        self.requirements: List[Requirement] = []
        
    def analyze_requirements(self, user_input: str) -> Dict:
        """分析用户输入的需求"""
        prompt = f"""
        请分析以下需求，提取关键信息：
        {user_input}
        
        请以JSON格式返回，包含以下字段：
        - 功能模块列表
        - 非功能需求列表
        - 业务规则和约束条件
        - 优先级建议
        """
        
        response = self.llm_client.chat(prompt)
        try:
            analysis = json.loads(response)
            return analysis
        except:
            return {"error": "需求解析失败，请重试"}
    
    def generate_use_case_diagram(self, requirements: List[Requirement]) -> str:
        """生成用例图的PlantUML代码"""
        prompt = f"""
        请根据以下需求生成用例图的PlantUML代码：
        {json.dumps([req.dict() for req in requirements], ensure_ascii=False, indent=2)}
        
        要求：
        1. 使用PlantUML语法
        2. 包含所有功能需求作为用例
        3. 添加适当的角色（Actor）
        4. 使用合适的布局和样式
        5. 只返回PlantUML代码，不要包含其他说明
        """
        
        response = self.llm_client.chat(prompt)
        return response.strip()
    
    def generate_requirement_doc(self, requirements: List[Requirement]) -> str:
        """生成需求文档"""
        # 生成用户故事
        user_stories = self._generate_user_stories(requirements)
        
        # 生成用例图
        use_case_diagram = self._generate_use_case_diagram(requirements)
        
        # 生成需求规格说明书
        srs = self._generate_srs(requirements)
        
        # 组合成完整文档
        doc = f"""# 需求规格说明书

## 1. 用户故事
{user_stories}

## 2. 用例图
```mermaid
{use_case_diagram}
```

## 3. 详细需求
{srs}
"""
        return doc
    
    def _generate_user_stories(self, requirements: List[Requirement]) -> str:
        """生成用户故事"""
        stories = []
        for req in requirements:
            if req.type == "功能需求":
                story = f"""### {req.category}
- 作为[角色]
- 我想要[功能]
- 以便于[价值]
"""
                stories.append(story)
        return "\n".join(stories)
    
    def _generate_use_case_diagram(self, requirements: List[Requirement]) -> str:
        """生成用例图"""
        diagram = """graph TD
"""
        for req in requirements:
            if req.type == "功能需求":
                diagram += f"    {req.id}[{req.category}]\n"
        return diagram
    
    def _generate_srs(self, requirements: List[Requirement]) -> str:
        """生成需求规格说明书"""
        srs = []
        for req in requirements:
            section = f"""### {req.category}
- 描述：{req.description}
- 优先级：{req.priority}
- 验收标准：
"""
            for criteria in req.acceptance_criteria:
                section += f"  - {criteria}\n"
            srs.append(section)
        return "\n".join(srs)

    def generate_srs_with_template(self, user_input: str, clarify_history: list, template: str) -> str:
        """生成需求规格说明书"""
        prompt = f"""
        请根据以下需求生成需求规格说明书：
        {user_input}
        
        请以JSON格式返回，包含以下字段：
        - 需求分析
        - 澄清历史
        - 模板
        """
        
        response = self.llm_client.chat(prompt)
        try:
            analysis = json.loads(response)
            return analysis
        except:
            return {"error": "需求分析失败，请重试"}

# 全局变量
agent = None
agent_lock = threading.Lock()
agent_ready = threading.Event()

# 保存全局事件循环引用
agent_loop = None

class ChatRequest(BaseModel):
    message: str

# 需求分析相关模型
class RequirementRequest(BaseModel):
    message: str

class RequirementResponse(BaseModel):
    analysis: dict

class DocumentRequest(BaseModel):
    requirements: List[dict]

class DocumentResponse(BaseModel):
    document: str

class UseCaseDiagramRequest(BaseModel):
    requirements: List[dict]

class UseCaseDiagramResponse(BaseModel):
    plantuml_code: str
    image_url: str

class SrsTemplateRequest(BaseModel):
    user_input: str
    clarify_history: list
    template: str

class SrsTemplateResponse(BaseModel):
    srs: str

# 创建需求分析智能体实例
requirements_agent = RequirementsAnalysis()

# 启动 Agent 的异步任务
async def start_agent():
    global agent
    max_retries = 3
    retry_delay = 5  # 秒
    
    for attempt in range(max_retries):
        try:
            if agent is None:
                agent = Agent(api_key, base_url, model)
                await agent.setup()
                agent_ready.set()
                print(f"Agent 初始化成功 (尝试 {attempt + 1}/{max_retries})")
                return
        except Exception as e:
            print(f"Agent 初始化失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"等待 {retry_delay} 秒后重试...")
                await asyncio.sleep(retry_delay)
            else:
                print("已达到最大重试次数，Agent 初始化失败")
                agent = None
                raise

# 在后台线程中启动 Agent
def background_start_agent():
    global agent, agent_loop
    
    try:
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        agent_loop = loop
        
        # 初始化状态
        agent_ready.clear()
        
        # 初始化 Agent
        loop.run_until_complete(start_agent())
        
        print("Agent 初始化完成，事件循环运行中")
        loop.run_forever()
    except Exception as e:
        print(f"Agent 线程错误: {e}")
        if agent is not None:
            agent_ready.clear()
            agent = None
    finally:
        if loop.is_running():
            loop.stop()
        if not loop.is_closed():
            loop.close()

# 添加 Agent 状态检查函数
async def check_agent_status():
    """检查 Agent 状态并在需要时重新初始化"""
    global agent
    
    if agent is None or not agent_ready.is_set():
        print("Agent 未就绪，尝试重新初始化...")
        await start_agent()
    return agent is not None and agent_ready.is_set()

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "提供agent服务"}


@app.post("/chat")
async def chat(message: str = Form(...)):
    global agent, agent_loop
    
    if not agent or not agent_ready.is_set():
        return {"status": "error", "message": "Agent 尚未准备好，请稍后再试"}
    
    if agent_loop is None or agent_loop.is_closed():
        return {"status": "error", "message": "Agent事件循环未创建或已关闭"}
    
    # 创建一个Future对象，用于在agent线程中执行并获取结果
    response_future = concurrent.futures.Future()
    
    def run_chat_in_agent_thread():
        """在agent的事件循环中运行chat方法并设置Future结果"""
        try:
            # 创建协程
            coro = agent.chat(message)
            # 创建Task
            task = agent_loop.create_task(coro)
            
            # 添加回调函数以设置Future的结果
            def set_result(task):
                try:
                    result = task.result()
                    response_future.set_result(result)
                except Exception as e:
                    response_future.set_exception(e)
            
            task.add_done_callback(set_result)
        except Exception as e:
            response_future.set_exception(e)
    
    # 将函数调度到agent事件循环所在的线程中执行
    agent_loop.call_soon_threadsafe(run_chat_in_agent_thread)
    
    try:
        # 等待结果，设置超时
        response = await asyncio.get_event_loop().run_in_executor(
            None, 
            functools.partial(response_future.result, timeout=300)
        )
        
        # 检查并处理返回值类型
        if response is None:
            return {"status": "error", "message": "Agent 返回了空回复"}
        elif isinstance(response, str):
            return {"status": "success", "message": response}
        else:
            try:
                return {"status": "success", "message": str(response)}
            except:
                return {"status": "error", "message": "无法处理 Agent 返回的非字符串格式回复"}
    except concurrent.futures.TimeoutError:
        return {"status": "error", "message": "请求超时，请尝试简化问题或稍后重试"}
    except Exception as e:
        print(f"处理消息时出错: {e}")
        return {"status": "error", "message": f"处理消息时出错: {str(e)}"}

@app.post("/create_or_update_index")
async def create_or_update_index(
    files: List[UploadFile] = File(...),
    name: str = Form(...)
):
    global agent, agent_loop
    
    if not name:
        raise HTTPException(status_code=400, detail="请提供知识库名称")

    # 创建知识库目录
    kb_dir = os.path.join(KNOWLEDGE_DIR, name)
    os.makedirs(kb_dir, exist_ok=True)
    
    # 保存上传的文件
    file_paths = []
    try:
        for file in files:
            print(f"处理文件: {file.filename}")
            dest_path = os.path.join(kb_dir, file.filename)
            
            # 读取上传的文件内容并写入目标位置
            with open(dest_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
                
            file_paths.append(dest_path)
            print(f"已保存文件到: {dest_path}")

    except Exception as e:
        return {"status": "error", "message": f"创建知识库时出错: {str(e)}"}
    
    # 在Agent的事件循环中创建向量存储
    response_future = concurrent.futures.Future()
    
    def run_create_index():
        try:
            coro = agent.create_index(files_dir=kb_dir, label=name)
            task = agent_loop.create_task(coro)
            
            def set_result(task):
                try:
                    result = task.result()
                    response_future.set_result(result)
                except Exception as e:
                    response_future.set_exception(e)
            
            task.add_done_callback(set_result)
        except Exception as e:
            response_future.set_exception(e)
    
    # 将函数调度到agent事件循环中执行
    agent_loop.call_soon_threadsafe(run_create_index)
    
    try:
        # 等待结果
        await asyncio.get_event_loop().run_in_executor(
            None, 
            functools.partial(response_future.result, timeout=120)
        )
        return {"status": "success", "message": f"成功创建/更新知识库: {name}，包含 {len(file_paths)} 个文件"}
    except Exception as e:
        return {"status": "error", "message": f"创建向量存储时出错: {str(e)}"}

@app.get("/list_knowledge_bases")
async def list_knowledge_bases():
    return {"status": "success", "knowledge_bases": [os.path.basename(dir) for dir in os.listdir(KNOWLEDGE_DIR)]}

@app.post("/delete_knowledge_base")
async def delete_knowledge_base(name: str = Form(...)):
    if not name:
        raise HTTPException(status_code=400, detail="请提供知识库名称")
    
    global agent, agent_loop    

    response_future = concurrent.futures.Future()

    def run_delete_knowledge_base():
        coro = agent.delete_index(name)
        task = agent_loop.create_task(coro)

        def set_result(task):
            try:
                result = task.result()
                response_future.set_result(result)
            except Exception as e:
                response_future.set_exception(e)

        task.add_done_callback(set_result)


    agent_loop.call_soon_threadsafe(run_delete_knowledge_base)

    try:
        await asyncio.get_event_loop().run_in_executor( 
            None, 
            functools.partial(response_future.result, timeout=30)
            )
        return {"status": "success", "message": f"成功删除知识库: {name}"}
    except Exception as e:
        return {"status": "error", "message": f"删除知识库时出错: {str(e)}"}

@app.post("/update_label")
async def update_label(name: str = Form(...)):
    global agent, agent_loop

    if not name:
        raise HTTPException(status_code=400, detail="请提供知识库名称")
    
    if not agent or not agent_ready.is_set():
        return {"status": "error", "message": "Agent 尚未准备好，请稍后再试"}
    
    if agent_loop is None or agent_loop.is_closed():
        return {"status": "error", "message": "Agent事件循环未创建或已关闭"}

    response_future = concurrent.futures.Future()

    def run_update_label():
        try:
            coro = agent.update_label(name)
            task = agent_loop.create_task(coro)

            def set_result(task):
                try:
                    result = task.result()
                    response_future.set_result(result)
                except Exception as e:
                    response_future.set_exception(e)
            
            task.add_done_callback(set_result)
        except Exception as e:
            response_future.set_exception(e)

    agent_loop.call_soon_threadsafe(run_update_label) # 将任务调度到agent事件循环所在的线程中执行

    try:
        # 等待结果
        await asyncio.get_event_loop().run_in_executor(
            None, 
            functools.partial(response_future.result, timeout=30)
        )
        return {"status": "success", "message": f"成功更新知识库标签: {name}"}
    except Exception as e:
        return {"status": "error", "message": f"更新知识库标签时出错: {str(e)}"}

@app.post("/analyze_requirements", response_model=RequirementResponse)
async def analyze_requirements(request: RequirementRequest):
    """分析需求并返回结构化结果"""
    try:
        # 检查 Agent 状态
        if not await check_agent_status():
            raise HTTPException(status_code=503, detail="Agent 服务不可用")
            
        # 分析需求
        analysis = requirements_agent.analyze_requirements(request.message)
        return {"analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"需求分析失败: {str(e)}")

@app.post("/generate_requirement_doc", response_model=DocumentResponse)
async def generate_requirement_doc(request: DocumentRequest):
    """生成需求文档"""
    try:
        # 检查 Agent 状态
        if not await check_agent_status():
            raise HTTPException(status_code=503, detail="Agent 服务不可用")
            
        # 将请求数据转换为 Requirement 对象
        requirements = [
            Requirement(**req) for req in request.requirements
        ]
        
        # 生成文档
        document = requirements_agent.generate_requirement_doc(requirements)
        return {"document": document}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档生成失败: {str(e)}")

@app.post("/generate_use_case_diagram", response_model=UseCaseDiagramResponse)
async def generate_use_case_diagram(request: UseCaseDiagramRequest):
    """生成用例图"""
    try:
        # 将字典转换为Requirement对象
        requirements = [
            Requirement(
                id=f"req_{i}",
                type=req.get("type", "功能需求"),
                category=req.get("category", ""),
                description=req.get("description", ""),
                priority=req.get("priority", "中"),
                dependencies=req.get("dependencies", []),
                acceptance_criteria=req.get("acceptance_criteria", [])
            )
            for i, req in enumerate(request.requirements)
        ]
        
        # 生成PlantUML代码
        plantuml_code = requirements_agent.generate_use_case_diagram(requirements)
        
        # 使用PlantUML服务生成图片
        plantuml_url = "http://www.plantuml.com/plantuml/png/"
        encoded_code = base64.b64encode(plantuml_code.encode()).decode()
        image_url = f"{plantuml_url}{encoded_code}"
        
        return UseCaseDiagramResponse(
            plantuml_code=plantuml_code,
            image_url=image_url
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_srs_with_template", response_model=SrsTemplateResponse)
async def generate_srs_with_template(request: SrsTemplateRequest):
    srs = requirements_agent.generate_srs_with_template(
        request.user_input, request.clarify_history, request.template
    )
    return SrsTemplateResponse(srs=srs)

if __name__ == "__main__":
    # 启动后台线程
    agent_thread = threading.Thread(target=background_start_agent, daemon=True)
    agent_thread.start()
    
    # 等待agent初始化
    timeout = 30  # 30秒超时
    start_time = time.time()
    while not agent_ready.is_set() and time.time() - start_time < timeout:
        time.sleep(0.5)
    
    if not agent_ready.is_set():
        print("警告: Agent初始化超时，API服务可能无法正常工作")
    
    # 禁用uvicorn的热重载功能
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)