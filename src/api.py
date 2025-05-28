from agent import Agent 
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, APIRouter, Body
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import threading
import os
from pydantic import BaseModel
import asyncio
import uvicorn
import time
from typing import List, Any, Callable, TypeVar, Awaitable
import shutil
import concurrent.futures
import functools
from umlAgent import UML_Agent
from fastapi.staticfiles import StaticFiles
from enum import Enum
from fastapi import Query
from questionAgent import questionAgent
from explainAgent import ExplainAgent
from typing import Optional
import json
from questionAgent import QuestionDifficulty, QuestionType

load_dotenv()
api_key = os.getenv("DASHSCOPE_API_KEY")
base_url = os.getenv("DASHSCOPE_BASE_URL")
model = 'qwen-plus'

# 确保必要的目录存在
KNOWLEDGE_DIR = os.path.join(os.getenv("PROJECT_PATH"), "knowledge_base")
VECTOR_STORE_DIR = os.path.join(os.getenv("PROJECT_PATH"), "VectorStore")

PROJECT_ROOT = os.getenv("PROJECT_PATH")



# 全局变量
agent = Agent(api_key, base_url, model) 
agent_lock = threading.Lock()
agent_ready = threading.Event()
umlAgent = UML_Agent(api_key, base_url, model)
explainAgent = ExplainAgent(api_key, base_url, model)
question_agent = questionAgent(api_key, base_url, model)

agents = [agent, umlAgent, explainAgent, question_agent]


# 保存全局事件循环引用
agent_loop = None

# 确保存放UML图片的目录存在
UML_STATIC_DIR = os.path.join(os.getenv("PROJECT_PATH"), "static")
os.makedirs(UML_STATIC_DIR, exist_ok=True)

# 确保文档输出目录存在
DOCS_DIR = os.path.join(os.getenv("PROJECT_PATH"), "static", "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

class ChatRequest(BaseModel):
    message: str


# uml图类型
UML_TYPES = [
    "class", "sequence", "activity", "usecase", 
    "state", "component", "deployment", "object"
]

# 定义类型变量，用于泛型函数
T = TypeVar('T')

# 定义UML图类型枚举
class DiagramType(str, Enum):
    CLASS = "class"
    SEQUENCE = "sequence"
    ACTIVITY = "activity"
    USECASE = "usecase"
    STATE = "state"
    COMPONENT = "component"
    DEPLOYMENT = "deployment"
    OBJECT = "object"



# 定义解释风格枚举
    '''
    解释风格：
    - 严谨
    - 通俗
    - 专业
    - 简洁
    - 风趣
    '''
class ExplainStyle(str, Enum):
    STRICT = "STRICT"
    POPULAR = "POPULAR"
    PROFESSIONAL = "PROFESSIONAL"
    CONCISE = "CONCISE"
    FUNNY = "FUNNY"


# 工具函数
async def run_in_agent_thread(
    coro_func: Callable[..., Awaitable[T]], 
    *args, 
    timeout: int = 300,
    **kwargs
) -> T:
    """
    在Agent线程的事件循环中执行异步函数，并等待结果
    
    Args:
        coro_func: 要执行的异步函数
        *args: 传递给异步函数的位置参数
        timeout: 等待结果的超时时间（秒）
        **kwargs: 传递给异步函数的关键字参数
        
    Returns:
        异步函数的执行结果
        
    Raises:
        concurrent.futures.TimeoutError: 如果等待超时
        Exception: 如果异步函数执行出错
    """
    global agent_loop
    
    if agent_loop is None or agent_loop.is_closed():
        raise RuntimeError("Agent事件循环未创建或已关闭")
    
    # 创建Future对象，用于在线程间传递结果
    response_future = concurrent.futures.Future()
    
    def run_in_loop():
        """在agent事件循环中运行协程并设置Future结果"""
        try:
            # 创建协程
            coro = coro_func(*args, **kwargs)
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
    agent_loop.call_soon_threadsafe(run_in_loop)
    
    # 等待结果
    return await asyncio.get_event_loop().run_in_executor(
        None, 
        functools.partial(response_future.result, timeout=timeout)
    )

class ErrorTrackingRequest(BaseModel):
    question: str
    user_answer: str
    correct: bool

class StepByStepRequest(BaseModel):
    question: str

# 启动 Agent 的异步任务
async def start_agent():
    global agent
    try:
        for agt in agents:
            await agt.setup()
        agent_ready.set()
        print("Agent 初始化完成")
    except Exception as e:
        print(f"Agent 初始化失败: {e}")
        agent = None

# 在后台线程中启动 Agent
def background_start_agent():
    """在后台线程中初始化Agent并保持事件循环运行"""
    global  agent_loop
    
    # 创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # 保存全局引用
    agent_loop = loop
    
    # 初始化Agent
    try:
        loop.run_until_complete(start_agent())
        print("Agent已初始化，事件循环继续运行")
        loop.run_forever()
    except Exception as e:
        print(f"Agent初始化或运行时出错: {e}")
    finally:
        # 仅在程序退出时关闭循环
        if loop.is_running():
            loop.stop()
        if not loop.is_closed():
            loop.close()

app = FastAPI()

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory=UML_STATIC_DIR), name="static")


@app.get("/")
async def root():
    """
    API根路径，返回服务状态信息
    
    Returns:
        dict: 包含服务状态信息的字典
    """
    return {"message": "提供agent服务"}

@app.post("/chat")
async def chat(message: str = Form(...)):
    """
    处理用户与Agent的对话请求
    
    Args:
        message (str): 用户发送的消息内容
        
    Returns:
        dict: 包含状态和回复消息的字典
        {
            "status": "success"/"error",
            "message": str
        }
    """
    if not agent or not agent_ready.is_set():
        return {"status": "error", "message": "Agent 尚未准备好，请稍后再试"}
    
    try:
        # 在Agent线程的事件循环中执行异步函数
        response = await run_in_agent_thread(agent.chat, message, timeout=300)
        
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
    """
    创建或更新知识库索引
    
    Args:
        files (List[UploadFile]): 上传的文件列表
        name (str): 知识库名称
        
    Returns:
        dict: 包含操作状态和消息的字典
        {
            "status": "success"/"error",
            "message": str
        }
    """
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
    
    
    
    try:
        # 等待结果
        await run_in_agent_thread(agent.create_index, files_dir=kb_dir, label=name, timeout=120)
        return {"status": "success", "message": f"成功创建/更新知识库: {name}，包含 {len(file_paths)} 个文件"}
    except Exception as e:
        return {"status": "error", "message": f"创建向量存储时出错: {str(e)}"}

@app.get("/list_knowledge_bases")
async def list_knowledge_bases():
    """
    获取所有知识库列表
    
    Returns:
        dict: 包含知识库列表的字典
        {
            "status": "success",
            "knowledge_bases": List[str]
        }
    """
    return {"status": "success", "knowledge_bases": [os.path.basename(dir) for dir in os.listdir(KNOWLEDGE_DIR)]}

@app.post("/delete_knowledge_base")
async def delete_knowledge_base(name: str = Form(...)):
    """
    删除指定的知识库
    
    Args:
        name (str): 要删除的知识库名称
        
    Returns:
        dict: 包含操作状态和消息的字典
        {
            "status": "success"/"error",
            "message": str
        }
    """
    if not name:
        raise HTTPException(status_code=400, detail="请提供知识库名称")
    
    try:
        await run_in_agent_thread(agent.delete_index, name, timeout=30)
        return {"status": "success", "message": f"成功删除知识库: {name}"}
    except Exception as e:
        return {"status": "error", "message": f"删除知识库时出错: {str(e)}"}


@app.post("/update_label")
async def update_label(name: str = Form(...)):
    """
    更新所有Agent使用的知识库标签
    
    Args:
        name (str): 知识库标签名称
        
    Returns:
        dict: 包含操作状态和消息的字典
        {
            "status": "success"/"error",
            "message": str
        }
    """
    if not name:
        raise HTTPException(status_code=400, detail="请提供知识库名称")
    
    if not agent or not agent_ready.is_set():
        return {"status": "error", "message": "Agent 尚未准备好，请稍后再试"}
    
    if agent_loop is None or agent_loop.is_closed():
        return {"status": "error", "message": "Agent事件循环未创建或已关闭"}


    # 检查label是否存在
    if name not in os.listdir(KNOWLEDGE_DIR):
        return {"status": "error", "message": f"知识库{name}不存在"}

    try:
        # 等待结果
        for agt in agents:
            await run_in_agent_thread(agt.update_label, name, timeout=30)

        return {"status": "success", "message": f"成功更新知识库标签: {name}"}
    except Exception as e:
        return {"status": "error", "message": f"更新知识库标签时出错: {str(e)}"}

@app.post("/umlAgent/generate_uml")
async def generate_uml(
    query: str = Form(...),
    diagram_type: DiagramType = Form(...)
):
    """
    生成UML图
    
    Args:
        query (str): 用户的UML图生成请求
        diagram_type (DiagramType): UML图类型，支持的类型包括：class, sequence, activity等
        
    Returns:
        dict: 包含生成的UML图信息的字典
        {
            "status": "success"/"error",
            "message": str,
            "static_path": str,
        }
    """
    try:
        # 现在diagram_type已经是枚举类型，可以直接使用其值
        result = await run_in_agent_thread(umlAgent.generate_uml, query, diagram_type.value, timeout=120)
        

        print(f"画图结果：{result}")

        return {"status": "success", "message": result['message'], "static_path": f"http://localhost:8000/static/{diagram_type.value}/uml.png"}

    except Exception as e:
        # 处理其他异常
        return {"status": "error", "message": f"生成UML图时出错: {str(e)}", "static_path": ""}

@app.post("/explainAgent/explain")
async def explain(
    query: str = Form(...),
    style_label: ExplainStyle = Form(...),
    output_file_name: str = Form(None),
    bing_search: bool = Form(False)
):
    """
    处理概念解释请求
    """
    try:
        # 使用位置参数调用
        response = await run_in_agent_thread(
            explainAgent.chat,
            query,                  # 第一个参数
            style_label.value,      # 第二个参数
            output_file_name,       # 第三个参数
            bing_search,            # 第四个参数
            timeout=120             # timeout是run_in_agent_thread的参数
        )
        
        # 如果指定了输出文件名，保存解释内容到文件
        if output_file_name:
            response["download_url"] = f"/download/{output_file_name}"
        
        return response
    except Exception as e:
        print(f"Error in explain endpoint: {str(e)}")
        return {"status": "error", "message": f"生成解释时出错: {str(e)}"}

@app.post("/questionAgent/explain_question")
async def explain_question(
    question: str = Form(...),
):
    """
    解释用户输入的题目
    message:
        {{
            "explanation": "详细解释",
            "key_points": ["考察重点1", "考察重点2", ...],
            "reference_answer": "参考答案"
        }}
    """
    try:
        result = await question_agent.explain_question(question)

        return {"status": "success", "data": result['message']}
    except Exception as e:
        return {"status": "error", "message": f"解释题目时出错: {str(e)}"}

@app.post("/questionAgent/generate_practice_set")
async def generate_practice_set(
    topics: str = Form(...),
    num_questions: int = Form(5),
    difficulty: QuestionDifficulty = QuestionDifficulty.MEDIUM
):
    """
    生成练习题

    data:
        {{
            "questions": [
                {{
                    "id": 1,
                    "type": "题目类型",
                    "question": "题目描述",
                    "options": ["选项1", "选项2", ...],  // 选择题必须提供
                    "reference_answer": "参考答案",
                    "analysis": "解题思路",
                    "topics": ["涉及知识点1", "涉及知识点2", ...]
                }},
                ...
            ],
            "total_points": 总分,
            "estimated_time": "预计完成时间（分钟）",
            "difficulty_distribution": {{
                "easy": 简单题数量,
                "medium": 中等题数量,
                "hard": 困难题数量
            }}
        }}
    """
    try:
        # 将接收到的字符串转换为列表
        topic_list = [topic.strip() for topic in topics.split(",") if topic.strip()]
        
        # 调用question_agent时传入处理后的列表
        result = await question_agent.generate_practice_set(topic_list, num_questions, difficulty)
        return {"status": "success", "data": result['message']}
    except Exception as e:
        return {"status": "error", "message": f"生成练习题时出错: {str(e)}"}

@app.post("/questionAgent/grade_practice_set")
async def grade_practice_set(
    practice_set: str = Form(...),  # 题目集的JSON字符串
    student_answers: str = Form(...),  # 学生答案集的JSON字符串
    reference_answers: str = Form(...)  # 参考答案集的JSON字符串
):
    """
    批改练习题集
    
    Args:
        practice_set: 题目集的JSON字符串
        reference_answers: 参考答案集的JSON字符串
        
    Returns:
        dict: 包含批改结果的字典
        {
            "status": "success"/"error",
            "data": {
                "score": float,  # 总分
                "scoring_points": [  # 得分点详情
                    {
                        "id": str,  # 题目ID
                        "point": str,  # 得分/失分点描述
                        "score": float,  # 得分
                        "deduction": float  # 扣分（如果是失分点）
                    },
                    ...
                ],
                "comments": str,  # 总体评价
                "suggestions": List[str],  # 改进建议
                "highlights": List[str]  # 亮点
            }
        }
    """
    try:
        # 解析JSON字符串
        try:
            practice_set_data = json.loads(practice_set)
            reference_answers_data = json.loads(reference_answers)
            student_answers_data = json.loads(student_answers)
        except json.JSONDecodeError:
            return {
                "status": "error",
                "message": "输入数据格式错误，请确保是有效的JSON格式"
            }
        
        # 调用question_agent的批改方法
        result = await question_agent.grade_practice_set(
            practice_set=practice_set_data,
            student_answers=student_answers_data,
            reference_answers=reference_answers_data    
        )
        
        if result["status"] == "success":
            return {
                "status": "success",
                "data": result["message"]
            }
        else:
            return {
                "status": "error",
                "message": result["message"]
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"批改练习题集时出错: {str(e)}"
        }

# 添加新的下载端点
@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    下载生成的解释文件
    
    Args:
        filename: 文件名
        
    Returns:
        FileResponse: 文件下载响应
    """
    file_path = os.path.join(DOCS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
        
    return FileResponse(
        file_path,
        media_type='application/octet-stream',
        filename=filename
    )




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