import os
import asyncio
import threading
import gradio as gr
from dotenv import load_dotenv
import time
from pathlib import Path
import json
import shutil
import httpx
import requests
# 导入你的 Agent 相关模块
from questionAgent import questionAgent
from retrieve import Retriever
from vectorStore import VectorStore
from enum import Enum
from typing import List, Dict
# 加载环境变量
load_dotenv()

PROJECT_PATH = os.getenv("PROJECT_PATH")

current_practice_set = None

examples = [
    "给我出一道考察数据流程图的习题",
    "总结我的知识盲点",
    "如何证明贪心算法的最优子结构性质？"
]

# 添加解释风格枚举
class ExplainStyle(str, Enum):
    SIMPLE = "简单解释"
    DETAILED = "详细解释"
    ACADEMIC = "学术风格"
    METAPHOR = "比喻解释"
    STEP = "步骤分解"
    EXAMPLE = "示例讲解"
    VISUAL = "可视化解释"
    COMPARATIVE = "对比解释"

# 修改API调用函数
async def get_concept_explanation(concept: str, style: str) -> dict:
    """
    调用概念解释API
    
    Args:
        concept: 要解释的概念
        style: 解释风格
        
    Returns:
        dict: 包含解释内容和相关概念的响应
    """
    try:
        api_url = "http://localhost:8000/explainAgent/explain"  # 修改为正确的API端点
        
        # 将中文风格名称转换为后端枚举值
        style_map = {
            "简单解释": "CONCISE",
            "详细解释": "STRICT",
            "学术风格": "PROFESSIONAL",
            "比喻解释": "POPULAR",
            "步骤分解": "STRICT",
            "示例讲解": "POPULAR",
            "可视化解释": "POPULAR",
            "对比解释": "PROFESSIONAL"
        }
        
        data = {
            "query": concept,
            "style_label": style_map.get(style, "CONCISE")
        }
        
        timeout = httpx.Timeout(30.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(api_url, data=data)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "explanation": result.get("message", "未获取到解释"),
                    "related_concepts": [],  # 后端暂时没有返回相关概念
                    "error": None
                }
            else:
                return {
                    "explanation": f"请求失败: {response.status_code}",
                    "related_concepts": [],
                    "error": response.text
                }
                
    except Exception as e:
        return {
            "explanation": f"发生错误: {str(e)}",
            "related_concepts": [],
            "error": str(e)
        }

# 修改为使用HTTP请求的版本
async def send_message_to_agent(message):
    """
    向后端API发送聊天消息的请求
    
    Args:
        message: 用户输入的消息
    
    Returns:
        str: 获取到的AI回复
    """
    try:
        # API端点和参数配置
        api_url = "http://localhost:8000/chat"

        data = {
            "message": message
        }
        
        timeout = httpx.Timeout(10000.0, connect=5.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                api_url,

                data=data
            )
            
            # 检查响应状态
            if response.status_code == 200:
                result = response.json()
                if "message" in result:
                    return result["message"]
                else:
                    return str(result)
            else:
                return f"请求失败，状态码: {response.status_code}, 原因: {response.text}"
                
    except httpx.RequestError as e:
        # 处理网络错误
        return f"网络请求错误: {str(e)}"
    except Exception as e:
        # 处理其他未知错误
        return f"处理消息时出错: {str(e)}"

# 创建或更新知识库
async def create_or_update_knowledge_base(files, name):
    """
    创建或更新知识库
    
    Args:
        files: 上传的文件列表
        name: 知识库名称
        
    Returns:
        str: 操作结果消息
    """
    try:
        # API端点
        api_url = "http://localhost:8000/create_or_update_index"
        
        # 准备文件数据，转换为与api_test相同的格式
        file_tuples = []
        for file in files:
            file_name = os.path.basename(file.name)
            # 以二进制模式打开文件
            file_content = open(file.name, "rb")
            # 构建文件元组：(表单字段名, (文件名, 文件内容))
            file_tuples.append(("files", (file_name, file_content)))
        
        # 准备表单数据
        form_data = {"name": name}

        # 设置超时，避免长时间等待
        timeout = httpx.Timeout(10000.0, connect=5.0)


        # 在线程池中执行请求      
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                api_url,
                files=file_tuples,
                data=form_data
            )
        
            # 处理响应
            if response.status_code == 200:
                result = response.json()
                if "message" in result:
                    return result["message"]
                else:
                    return str(result)
            else:
                return f"请求失败，状态码: {response.status_code}, 原因: {response.text}"
            
    except Exception as e:
        return f"创建或更新知识库时出错: {str(e)}"
    

# 删除知识库
async def delete_knowledge_base(name):
    try:
        # API端点和参数配置
        api_url = "http://localhost:8000/delete_knowledge_base"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "name": name
        }
        
        # 设置超时，避免长时间等待
        timeout = httpx.Timeout(30.0, connect=5.0)
        
        # 发送异步HTTP请求
        async with httpx.AsyncClient(timeout=timeout) as client:    
            response = await client.post(
                api_url,
                headers=headers,
                data=data
            )
            
        # 检查响应状态
        if response.status_code == 200:
            result = response.json()
            if "message" in result:
                return result["message"]
            else:
                return str(result)
        else:
            return f"请求失败，状态码: {response.status_code}, 原因: {response.text}"
                
    except httpx.RequestError as e:
        # 处理网络错误
        return f"网络请求错误: {str(e)}"
    except httpx.TimeoutException:
        # 处理超时错误
        return "请求超时，请稍后再试"
    except Exception as e:
        # 处理其他未知错误
        return f"处理消息时出错: {str(e)}"
    

# 列出所有知识库
async def list_knowledge_bases():
    try:
        url = "http://localhost:8000/list_knowledge_bases"
        # 异步
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            result = response.json()
            if "knowledge_bases" in result:
                return result["knowledge_bases"]
            else:
                return str(result)
    except Exception as e:
        return f"获取知识库列表时出错: {str(e)}"

# 选择知识库
async def select_knowledge_base(kb_name):
    try:
        url = "http://localhost:8000/update_label"
        data = {"name": kb_name}
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            result = response.json()
            if "message" in result:
                return result["message"]
            else:
                return str(result)
    except Exception as e:
        return f"选择知识库时出错: {str(e)}"




# 修改处理聊天消息的函数
async def process_message(message, history):
    if not message or not message.strip():
        return "请输入有效的消息"
        
    print(f"处理消息: {message}")
    try:
        # 异步
        response =  await send_message_to_agent(message)
        print(f"收到回复: {response[:100]}...")
        return response
    except Exception as e:
        print(f"处理消息时出错: {e}")
        return f"处理消息时出错: {str(e)}"


# 消息处理功能
def user_message(user_message, history):
    if not user_message:
        return "", history
    return "", history + [{"role": "user", "content": user_message}]

async def bot_message(history):
    try:
        user_message = history[-1]["content"]
        # 异步
        bot_message = await process_message(user_message, history[:-1])
        return history + [{"role": "assistant", "content": bot_message}]
    except Exception as e:
        print(f"处理消息时出错: {e}")
        return history + [{"role": "assistant", "content": f"处理消息时出错: {str(e)}"}]

# 清空聊天
def clear_chat():
    return None

async def refresh_knowledge_bases():
    kb_list = await list_knowledge_bases()
    return gr.update(choices=kb_list)

async def refresh_delete_knowledge_bases():
    kb_list = await list_knowledge_bases()
    return gr.update(choices=kb_list)

async def display_knowledge_bases():
    kb_list = await list_knowledge_bases()
    
    text = ""
    for kb in kb_list:
        text += f"{kb}\n"
    return text


async def init_knowledge_bases():
    kb_list = await list_knowledge_bases()
    return gr.update(choices=kb_list), gr.update(choices=kb_list), await display_knowledge_bases()


# 创建 Gradio 界面 - 优化样式版本
with gr.Blocks(
    title="智能Agent助手",
    theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="blue", neutral_hue="slate"),
    css="""
    /* 全局样式 */
    body, .gradio-container {
        background-color: #f0f4f8 !important;
        font-family: "Segoe UI", Arial, sans-serif;
    }
    
    /* 标题和页面顶部 */
    #header {
        background: linear-gradient(135deg, #4b6cb7 0%, #182848 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        color: white;
    }
    
    #header img {
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
    }
    
    #title {
        color: white !important;
        font-size: 28px !important;
        margin: 0;
        padding: 0;
    }
    
    #subtitle {
        color: rgba(255, 255, 255, 0.9) !important;
        margin-top: 5px;
    }
    
    /* 聊天界面 */
    #chat_tab .container {
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        padding: 20px;
    }
    
    #chatbot {
        height: 500px;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        overflow: hidden;
        background: white;
    }
    
    #chatbot .message.user {
        background: #e9f2ff !important;
        border-radius: 18px 18px 4px 18px;
        padding: 10px 15px;
        margin: 8px;
    }
    
    #chatbot .message.bot {
        background: #f0f7ff !important;
        border-radius: 18px 18px 18px 4px;
        padding: 10px 15px;
        margin: 8px;
    }
    
    /* 修复头像大小与圆形边框不匹配问题 */
    #chatbot .message-avatar {
        width: 40px !important;
        height: 40px !important;
        border-radius: 50% !important;
        overflow: hidden !important;
    }
    
    #chatbot .message-avatar img {
        width: 100% !important;
        height: 100% !important;
        object-fit: cover !important;
        object-position: center !important;
    }
    
    /* 输入区域 */
    #message_box {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 10px;
        font-size: 16px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        background: white;
    }
    
    /* 按钮样式 */
    button.primary {
        background: linear-gradient(135deg, #4b6cb7 0%, #182848 100%) !important;
        border: none !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1) !important;
        padding: 10px 20px !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    
    button.primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2) !important;
    }
    
    button.secondary {
        background: #f0f4f8 !important;
        color: #4b6cb7 !important;
        border: 1px solid #ddd !important;
        border-radius: 8px !important;
    }
    
    button.secondary:hover {
        background: #e9f2ff !important;
    }
    
    /* 右侧面板 */
    #sidebar {
        background: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    }
    
    /* 知识库管理标签页 */
    #kb_tab .container {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    }
    
    /* 分组和表格 */
    .gr-group {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        background: #fafbfd;
    }
    
    /* 下拉菜单 */
    select, .gr-dropdown {
        border-radius: 8px !important;
        border: 1px solid #ddd !important;
        padding: 8px !important;
        background-color: white !important;
    }
    
    /* 标签页导航 */
    .tabs > .tab-nav {
        background-color: transparent;
        margin-bottom: 20px;
    }
    
    .tabs > .tab-nav > button {
        font-size: 16px;
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
        margin-right: 5px;
        background: #e0e0e0;
        color: #555;
        border: none;
    }
    
    .tabs > .tab-nav > button.selected {
        background: #4b6cb7;
        color: white;
    }
    
    /* 文件上传区域 */
    .gr-file-drop {
        border: 2px dashed #ddd;
        border-radius: 10px;
        padding: 20px;
        background: #fafbfd;
        text-align: center;
    }
    
    /* 示例问题按钮 */
    #example1, #example2, #example3 {
        width: 100%;
        text-align: left;
        margin-bottom: 8px;
        padding: 8px 12px;
    }
    
    /* 添加搜索结果的样式 */
    .related-links {
        margin-top: 1rem;
        padding: 1rem;
        border-radius: 8px;
        background: #f8f9fa;
    }
    
    .related-links h3 {
        color: #2d3748;
        margin-bottom: 1rem;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.5rem;
    }
    
    .related-links a {
        color: #4a5568;
        text-decoration: none;
        transition: all 0.2s;
        display: block;
        padding: 0.5rem;
        border-radius: 4px;
        margin: 0.25rem 0;
    }
    
    .related-links a:hover {
        background: #edf2f7;
        color: #2b6cb0;
        transform: translateX(4px);
    }
    
    .related-links ol {
        list-style-type: none;
        counter-reset: item;
        padding-left: 0;
    }
    
    .related-links ol li {
        counter-increment: item;
        margin-bottom: 0.5rem;
        position: relative;
        padding-left: 2rem;
    }
    
    .related-links ol li:before {
        content: counter(item);
        background: #4a5568;
        color: white;
        width: 1.5rem;
        height: 1.5rem;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        position: absolute;
        left: 0;
        font-size: 0.875rem;
    }
    """
) as app:   
    gr.Markdown("# 🤖 软件工程课程助手", elem_id="title")
    gr.Markdown("#### LLM + MCP + RAG 驱动的智能问答与任务执行系统", elem_id="subtitle") 
    
    with gr.Tabs() as tabs:
        # 1. 通用对话Agent
        with gr.TabItem("💬 通用对话", id="chat_tab") as chat_tab:
            # 主要内容区域
            with gr.Row(equal_height=True):
                # 左侧聊天区域 (占据更多空间)
                with gr.Column(scale=5, elem_id="chat_column"):
                    # 聊天记录
                    chatbot = gr.Chatbot(
                        height=600, 
                        type="messages",
                        avatar_images=(f"{PROJECT_PATH}/images/logo_user.png", 
                                     f"{PROJECT_PATH}/images/logo_agent.png"),
                        elem_id="chatbot"
                    )
                    
                    # 底部输入区和按钮 - 使用新的布局
                    with gr.Row(equal_height=True, elem_id="input_row"):
                        msg = gr.Textbox(
                            placeholder="在这里输入您的问题...",
                            lines=2,
                            max_lines=6,
                            show_label=False,
                            elem_id="message_box",
                            container=False,
                            scale=5,
                            autofocus=True,  # 页面加载时自动聚焦到输入框
                        )
                        
                        # 按钮组 - 水平排列
                        with gr.Column(scale=1, min_width=100, elem_id="button_group"):
                            send_btn = gr.Button("发送", variant="primary", size="lg", elem_id="send_btn")
                            clear_btn = gr.Button("清空", size="sm", elem_id="clear_btn")
                
                # 右侧信息面板
                with gr.Column(scale=2, min_width=250, elem_id="sidebar"):
                    # 知识库选择区
                    with gr.Group(elem_id="kb_selector"):
                        gr.Markdown("### 📚 知识库选择")
                        with gr.Row():
                            kb_name_dropdown = gr.Dropdown(
                                label="当前知识库",
                                choices=[],
                                value=None,
                                interactive=True,
                                scale=3,
                                elem_id="kb_dropdown"
                            )
                            select_kb_btn = gr.Button("选择", variant="primary", size="sm", scale=1)

                    gr.Markdown("### 🔍 功能介绍", elem_id="features_title")
                    with gr.Group(elem_id="features_group"):
                        gr.Markdown("""
                        - ✅ 智能问答
                        - ✅ 知识检索
                        - ✅ 工具调用
                        - ✅ 文档处理
                        """)
                    
                    gr.Markdown("### 💡 示例问题", elem_id="examples_title")
                    with gr.Group(elem_id="examples_group"):
                        example_btn1 = gr.Button(examples[0], size="sm", elem_id="example1")
                        example_btn2 = gr.Button(examples[1], size="sm", elem_id="example2")
                        example_btn3 = gr.Button(examples[2], size="sm", elem_id="example3")

                    # 状态显示
                    with gr.Accordion("系统状态", open=True, elem_id="status_accordion"):
                        system_status = gr.Textbox(
                            label="状态", 
                            value="系统已就绪", 
                            interactive=False,
                            elem_id="system_status"
                        )
            
            # 示例问题的点击事件
            def use_example(example):
                return example
                
            example_btn1.click(use_example, [gr.State(examples[0])], [msg])
            example_btn2.click(use_example, [gr.State(examples[1])], [msg])
            example_btn3.click(use_example, [gr.State(examples[2])], [msg])
            

            
            # 绑定事件
            msg.submit(user_message, [msg, chatbot], [msg, chatbot], queue=False).then(
                bot_message, chatbot, chatbot
            )
            
            send_btn.click(user_message, [msg, chatbot], [msg, chatbot], queue=False).then(
                bot_message, chatbot, chatbot
            )
            
            clear_btn.click(clear_chat, None, chatbot, queue=False)
            
            select_kb_btn.click(select_knowledge_base, [kb_name_dropdown], [system_status])

        # 2. 概念解释Agent
        with gr.TabItem("📚 概念解释", id="explain_tab") as explain_tab:
            with gr.Row():
                # 左侧输入区域
                with gr.Column(scale=2):
                    concept_input = gr.Textbox(
                        label="概念",
                        placeholder="请输入要解释的概念...",
                        lines=2
                    )
                    with gr.Row():
                        explain_style = gr.Dropdown(
                            label="解释风格",
                            choices=[
                                "简单解释",  # CONCISE
                                "详细解释",  # STRICT
                                "专业解释",  # PROFESSIONAL
                                "通俗解释",  # POPULAR
                                "风趣解释"   # FUNNY
                            ],
                            value="简单解释"
                        )
                    
                    # 添加新的选项行
                    with gr.Row():
                        output_filename = gr.Textbox(
                            label="保存解释（可选）",
                            placeholder="输入一个文件名，例如：explanation.md",
                            value="",
                            interactive=True
                        )
                        enable_search = gr.Checkbox(
                            label="推荐相关资料",
                            value=True,
                            interactive=True
                        )
                    
                    explain_btn = gr.Button("生成解释", variant="primary")
                    
                    # 将相关链接移动到这里
                    with gr.Accordion("🔗 相关链接", open=True):
                        related_links = gr.Markdown(
                            value="暂无相关链接",
                            label="参考资料"
                        )
                
                # 右侧输出区域
                with gr.Column(scale=3):
                    # 状态显示
                    explain_status = gr.Markdown("准备就绪")
                    
                    # 解释内容
                    with gr.Group():
                        gr.Markdown("### 📝 解释内容")
                        explanation_output = gr.Markdown()
                    
            # 修改生成解释函数，简化返回值并在状态消息中添加下载链接
            async def generate_explanation(
                concept: str, 
                style: str, 
                output_filename: str,
                enable_search: bool
            ) -> tuple:
                """生成概念解释"""
                if not concept.strip():
                    return (
                        "请输入要解释的概念",
                        "⚠️ 错误：概念不能为空",
                        None
                    )
                
                try:
                    api_url = "http://localhost:8000/explainAgent/explain"
                    
                    # 风格映射表
                    style_mapping = {
                        "简单解释": "CONCISE",
                        "详细解释": "STRICT",
                        "专业解释": "PROFESSIONAL",
                        "通俗解释": "POPULAR",
                        "风趣解释": "FUNNY"
                    }
                    
                    # 准备请求数据
                    form_data = {
                        "query": concept,
                        "style_label": style_mapping[style],
                        "output_file_name": output_filename if output_filename.strip() else None,
                        "bing_search": str(enable_search).lower()
                    }
                    
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            api_url,
                            data=form_data,
                            timeout=120
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result["status"] == "success":
                                explanation = result["message"]
                                formatted_links = ""
                                
                                # 处理搜索结果
                                if "search_results" in result and enable_search:
                                    try:
                                        search_results = json.loads(result["search_results"])
                                        formatted_links = "### 📚 相关参考资料\n\n"
                                        for i, item in enumerate(search_results, 1):
                                            title = item.get("title", "").strip()
                                            link = item.get("link", "").strip()
                                            formatted_links += f"{i}. **[{title}]({link})**\n"
                                    except:
                                        formatted_links = "### ❌ 无法加载相关链接"
                                
                                # 生成状态消息，包含下载链接
                                if output_filename.strip():
                                    if "download_url" in result:
                                        download_url = f"http://localhost:8000{result['download_url']}"
                                        status_message = f"✅ 解释生成完成 | [📥 点击下载文件]({download_url})"
                                    elif "file_error" in result:
                                        status_message = "✅ 解释生成完成\n❌ 文件保存失败"
                                else:
                                    status_message = "✅ 解释生成完成"
                                
                                return (
                                    explanation,
                                    status_message,
                                    formatted_links
                                )
                            else:
                                return (
                                    "生成解释时出错",
                                    f"❌ 错误：{result['message']}",
                                    None
                                )
                        else:
                            return (
                                "请求失败",
                                f"❌ 错误：HTTP {response.status_code} - {response.text}",
                                None
                            )
                            
                except Exception as e:
                    print(f"Error in generate_explanation: {str(e)}")
                    return (
                        "生成解释时出错",
                        f"❌ 错误：{str(e)}",
                        None
                    )

            # 修改事件绑定
            explain_btn.click(
                lambda: "🤔 正在生成解释...",
                None,
                explain_status
            ).then(
                generate_explanation,
                inputs=[
                    concept_input, 
                    explain_style, 
                    output_filename,
                    enable_search
                ],
                outputs=[
                    explanation_output, 
                    explain_status, 
                    related_links
                ]
            )
            
        # 3. UML图生成Agent
        with gr.TabItem("📊 UML图生成", id="uml_tab") as uml_tab:
            with gr.Row():
                # 左侧输入区域
                with gr.Column(scale=2):
                    uml_input = gr.Textbox(
                        label="描述",
                        placeholder="请输入系统/类/流程的描述...",
                        lines=5
                    )
                    with gr.Row():
                        diagram_type = gr.Dropdown(
                            label="图表类型",
                            choices=[
                                "类图 (class)",
                                "序列图 (sequence)",
                                "活动图 (activity)",
                                "用例图 (usecase)",
                                "状态图 (state)",
                                "组件图 (component)",
                                "部署图 (deployment)",
                                "对象图 (object)"
                            ],
                            value="类图 (class)"
                        )
                        generate_btn = gr.Button("生成UML图", variant="primary")
                    
                    # 添加说明文本
                    with gr.Accordion("💡 使用说明", open=False):
                        gr.Markdown("""
                        ### 使用说明
                        1. **类图 (class)**: 描述类的属性、方法和类之间的关系
                        2. **序列图 (sequence)**: 展示对象之间的交互和消息传递
                        3. **活动图 (activity)**: 描述业务流程或算法的步骤
                        4. **用例图 (usecase)**: 展示系统功能和用户交互
                        5. **状态图 (state)**: 描述对象的状态变化
                        6. **组件图 (component)**: 展示系统的组件结构
                        7. **部署图 (deployment)**: 描述系统的物理部署
                        8. **对象图 (object)**: 展示系统在特定时刻的对象状态
                        """)
                
                # 右侧输出区域
                with gr.Column(scale=3):
                    # 状态显示
                    uml_status = gr.Markdown("准备就绪")
                    
                    # UML图片显示
                    uml_image = gr.Image(
                        label="生成的UML图",
                        type="filepath"
                    )
                    
                    # 图表说明
                    with gr.Accordion("📝 图表说明", open=True):
                        uml_explanation = gr.Markdown()
                    

    


            async def generate_uml(description: str, diagram_type: str) -> tuple:
                """生成UML图并返回结果"""
                if not description.strip():
                    return (
                        None,  # 图片路径
                        "⚠️ 错误：请输入UML描述",  # 状态
                        "",    # 说明
                    )
                
                try:
                    # 提取图表类型的英文标识
                    type_mapping = {
                        "类图 (class)": "class",
                        "序列图 (sequence)": "sequence",
                        "活动图 (activity)": "activity",
                        "用例图 (usecase)": "usecase",
                        "状态图 (state)": "state",
                        "组件图 (component)": "component",
                        "部署图 (deployment)": "deployment",
                        "对象图 (object)": "object"
                    }
                    
                    diagram_type_value = type_mapping[diagram_type]
                    
                    # 调用后端API
                    api_url = "http://localhost:8000/umlAgent/generate_uml"
                    form_data = {
                        "query": description,
                        "diagram_type": diagram_type_value
                    }
                    
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            api_url,
                            data=form_data,
                            timeout=120
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result["status"] == "success":
                                # 添加时间戳到图片URL以防止缓存
                                image_path = f"{result['static_path']}?t={int(time.time())}"
                                explanation = result["message"]
                                
                                print(f"生成UML图成功，图片路径：{image_path}")
                                
                                return (
                                    image_path,  # 图片路径
                                    "✅ UML图生成成功",  # 状态
                                    f"\n\n{explanation}",  # 说明
                                )
                            else:
                                return (
                                    None,
                                    f"❌ 错误：{result['message']}",
                                    ""
                                )
                        else:
                            return (
                                None,
                                f"❌ 错误：HTTP {response.status_code} - {response.text}",
                                ""
                            )
                            
                except Exception as e:
                    print(f"Error in generate_uml: {str(e)}")
                    return (
                        None,
                        f"❌ 错误：{str(e)}",
                        ""
                    )

            # 绑定生成按钮事件
            generate_btn.click(
                lambda: "🤔 正在生成UML图...",
                None,
                uml_status
            ).then(
                generate_uml,
                inputs=[
                    uml_input,
                    diagram_type
                ],
                outputs=[
                    uml_image,
                    uml_status,
                    uml_explanation,
               
                ]
            )

        # 4. 解题Agent
        with gr.TabItem("✏️ 智能解题", id="solve_tab") as solve_tab:
            with gr.Tabs() as solve_tabs:
                # 4.1 题目解答
                with gr.TabItem("💡 题目解答"):
                    with gr.Row():
                        # 左侧输入区域
                        with gr.Column(scale=2):
                            question_input = gr.Textbox(
                                label="题目",
                                placeholder="请输入要解答的软件工程相关题目...",
                                lines=4
                            )
                            
                            # 添加说明文本
                            with gr.Accordion("💡 使用说明", open=False):
                                gr.Markdown("""
                                ### 使用说明
                                1. 输入任何软件工程相关的题目
                                2. 系统会提供详细的解题思路和参考答案
                                3. 同时会分析题目的考察重点
                                4. 支持各类题型：概念题、案例题、设计题等
                                """)
                            
                            explain_question_btn = gr.Button("解答题目", variant="primary")
                        
                        # 右侧输出区域
                        with gr.Column(scale=3):
                            # 状态显示
                            explain_question_status = gr.Markdown("准备就绪")
                            
                            # 解释内容
                            with gr.Accordion("📝 解题思路", open=True):
                                explanation_question_output = gr.Markdown()
                            
                            # 考察重点
                            with gr.Accordion("🎯 考察重点", open=True):
                                key_points_output = gr.Markdown()
                            
                            # 参考答案
                            with gr.Accordion("✅ 参考答案", open=True):
                                reference_answer_output = gr.Markdown()

                # 4.2 练习测试
                with gr.TabItem("📝 练习测试"):
                    current_practice_set = gr.State(None)
                    with gr.Row():
                        # 左侧配置区域
                        with gr.Column(scale=2):
                            # 知识点选择
                            topics_input = gr.Textbox(
                                label="知识点",
                                placeholder="输入要练习的知识点，多个知识点用逗号分隔",
                                lines=2
                            )
                            
                            with gr.Row():
                                # 题目数量
                                num_questions = gr.Slider(
                                    minimum=1,
                                    maximum=10,
                                    value=3,
                                    step=1,
                                    label="题目数量"
                                )
                                
                                # 难度选择
                                difficulty = gr.Dropdown(
                                    choices=["简单", "中等", "困难"],
                                    value="中等",
                                    label="难度"
                                )
                            
                            generate_btn = gr.Button("生成练习", variant="primary")
                            
                            # 添加说明文本
                            with gr.Accordion("💡 使用说明", open=False):
                                gr.Markdown("""
                                ### 使用说明
                                1. 输入要练习的知识点，多个知识点用逗号分隔
                                2. 选择题目数量（1-10题）
                                3. 选择题目难度（简单/中等/困难）
                                4. 点击生成练习后，系统会生成相应的题目
                                5. 在答题区域输入你的答案，每个答案占一行
                                6. 完成答题后点击提交进行批改
                                """)
                        
                        # 右侧练习区域
                        with gr.Column(scale=3):
                            # 练习状态
                            practice_status = gr.Markdown("准备就绪")
                            
                            # 题目显示区域
                            with gr.Accordion("📝 题目", open=True):
                                questions_display = gr.Markdown()
                            
                            # 练习信息
                            with gr.Row():
                                total_points = gr.Markdown("总分：--", label="总分")
                                estimated_time = gr.Markdown("预计用时：--", label="预计用时")
                            
                            # 答题区域
                            answer_input = gr.Textbox(
                                label="你的答案",
                                placeholder="请在这里输入你的答案，每个答案占一行...",
                                lines=8,
                                interactive=True
                            )
                            
                            submit_btn = gr.Button("提交答案", interactive=True)
                            
                            # 批改结果
                            with gr.Accordion("📊 批改结果", open=True):
                                grading_result = gr.Markdown()


            async def solve_problem(question_input: str) -> tuple:
                api_url = "http://localhost:8000/questionAgent/explain_question"
                data = {
                    "question": question_input
                }



                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        api_url,
                        data=data, 
                        timeout=120
    
                    )

                    if response.status_code == 200:
                        result = response.json()
                        data = json.loads(result['data'])
                        explain_str = data['explanation']
                        key_points_str = '\n'.join(f"- {point}"   for point in data['key_points'])
                        ref_ans = data['reference_answer']

                        return (
                            "✅ 习题解答完成",
                            explain_str,
                            key_points_str,
                            ref_ans
                        )
                    
                    else:
                        return (
                             "⚠️ 错误",  # 状态
                            None,
                            None,
                            None
                        )
                    

            # 修改事件绑定
            explain_question_btn.click(
                lambda: "🤔 正在生成解答...",
                None,
                explain_question_status
            ).then(
                solve_problem,
                inputs=[
                    question_input
                ],
                outputs=[
                    explain_question_status,
                    explanation_question_output,
                    key_points_output,
                    reference_answer_output

                ]
            )

            # 实现生成练习集功能
            async def generate_practice_set(
                topics: str,
                num_questions: int,
                difficulty: str
            ) -> tuple:
                """生成练习题集并返回结果"""
                if not topics.strip():
                    return (
                        "⚠️ 错误：请输入知识点",  # 状态
                        "",  # 题目
                        "总分：--",  # 总分
                        "预计用时：--",  # 预计用时
                        None
                    )
                
                try:
                   
                    
                    if not topics:
                        return (
                            "⚠️ 错误：请输入有效的知识点",
                            "",
                            "总分：--",
                            "预计用时：--",
                            None
                        )
                    
                    # 难度映射
                    difficulty_mapping = {
                        "简单": "EASY",
                        "中等": "MEDIUM",
                        "困难": "HARD"
                    }
                    
                    # 调用后端API
                    api_url = "http://localhost:8000/questionAgent/generate_practice_set"
                    
                    # 准备请求数据
                    data = {
                        "topics": topics,
                        "num_questions": num_questions,
                        "difficulty": difficulty_mapping[difficulty]
                    }

                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            api_url,
                            data=data, 
                            timeout=120
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result["status"] == "success":
                                try:
                                    # 移除JavaScript风格的注释，然后再解析JSON
                                    data_str = result["data"]
                                    # 移除包含 // 的行
                                    cleaned_data = '\n'.join(line for line in data_str.split('\n') 
                                                           if '//' not in line)
                                    data = json.loads(cleaned_data)
                                    
                                    # 格式化题目显示
                                    questions_md = "\n\n"
                                    for q in data["questions"]:
                                        questions_md += f"#### {q['id']}. {q['question']}\n"
                                        if "options" in q and q["options"]:
                                            for opt in q["options"]:
                                                questions_md += f"{opt}\n"
                                        questions_md += "\n"
                                    
                 
                                    
                                    return (
                                        "✅ 练习题生成完成",  # 状态
                                        questions_md,  # 题目
                                        f"总分：{data['total_points']}分",  # 总分
                                        f"预计用时：{data['estimated_time']}分钟",  # 预计用时
                                        data,
                                    )
                                except json.JSONDecodeError as e:
                                    print(f"JSON解析错误: {str(e)}")
                                    print(f"原始数据: {result['data']}")
                                    return (
                                        f"❌ 错误：解析练习题数据失败",
                                        "",
                                        "总分：--",
                                        "预计用时：--",
                                        None
                                    )
                            else:
                                return (
                                    f"❌ 错误：{result['message']}",
                                    "",
                                    "总分：--",
                                    "预计用时：--",
                                    None
                                )
                        else:
                            return (
                                f"❌ 错误：HTTP {response.status_code} - {response.text}",
                                "",
                                "总分：--",
                                "预计用时：--",
                                None
                            )
                            
                except Exception as e:
                    print(f"Error in generate_practice_set: {str(e)}")
                    return (
                        f"❌ 错误：{str(e)}",
                        "",
                        "总分：--",
                        "预计用时：--",
                        None
                    )

            # 绑定生成按钮事件
            generate_btn.click(
                lambda: "🤔 正在生成练习题...",
                None,
                practice_status
            ).then(
                generate_practice_set,
                inputs=[
                    topics_input,
                    num_questions,
                    difficulty
                ],
                outputs=[
                    practice_status,
                    questions_display,
                    total_points,
                    estimated_time,
                    current_practice_set
                ]
            )


            async def grade_answers(
                answers: str,
                practice_set_data: Dict
            ) -> tuple:
                """批改学生答案并返回结果"""
                print(f"批改学生答案：{answers}")
                print(f"练习集数据：{practice_set_data}")

                try:
                    # 准备请求数据
                    api_url = "http://localhost:8000/questionAgent/grade_practice_set"
                    
                    # 将答案字符串转换为列表
                    student_answers = [ans.strip() for ans in answers.split("\n") if ans.strip()]
                    
                    # 准备请求数据
                    form_data = {
                        "practice_set": json.dumps(practice_set_data),
                        "student_answers": json.dumps(student_answers),
                        "reference_answers": json.dumps([q["reference_answer"] for q in practice_set_data["questions"]])
                    }
                    
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            api_url,
                            data=form_data,
                            timeout=120
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result["status"] == "success":
                                data = json.loads(result["data"])
                                
                                # 格式化批改结果显示
                                grading_md = "\n\n"
                                
                                # 总体情况
                                grading_md += f"#### 总体评价\n"
                                grading_md += f"- 总分：{data['score']}分\n"
                                grading_md += f"- 评语：{data['comments']}\n\n"
                                
                                # 具体得分点
                                grading_md += f"#### 详细评分\n"
                                for point in data['scoring_points']:
                                    if 'score' in point:
                                        grading_md += f"✅ 题目{point['id']}: {point['point']} (+{point['score']}分)\n"
                                    if 'deduction' in point:
                                        grading_md += f"❌ 题目{point['id']}: {point['point']} (-{point['deduction']}分)\n"
                                grading_md += "\n"
                                
                                # 改进建议
                                if data['suggestions']:
                                    grading_md += f"#### 改进建议\n"
                                    for suggestion in data['suggestions']:
                                        grading_md += f"- {suggestion}\n"
                                    grading_md += "\n"
                                
                                # 亮点
                                if data['highlights']:
                                    grading_md += f"#### 亮点\n"
                                    for highlight in data['highlights']:
                                        grading_md += f"- {highlight}\n"
                                
                                return (
                                    "✅ 批改完成",  # 状态
                                    grading_md,  # 批改结果
                                )
                            else:
                                return (
                                    f"❌ 错误：{result['message']}",  # 状态
                                    "",  # 批改结果
                                )
                        else:
                            return (
                                f"❌ 错误：HTTP {response.status_code} - {response.text}",
                                ""
                            )
                            
                except Exception as e:
                    print(f"Error in grade_answers: {str(e)}")
                    return (
                        f"❌ 错误：{str(e)}",
                        ""
                    )


            # 添加提交答案的事件绑定
            submit_btn.click(
                lambda: "🤔 正在批改答案...",
                None,
                practice_status
            ).then(
                grade_answers,
                inputs=[
                    answer_input,
                    current_practice_set  # 使用状态传递练习集数据
                ],
                outputs=[
                    practice_status,
                    grading_result
                ]
            )

        # 5. 知识库管理
        with gr.TabItem("📚 知识库管理", id="kb_tab") as kb_tab:  
            with gr.Row():  
                # 左侧知识库管理功能
                with gr.Column(scale=3, elem_id="kb_management"):
                    # 创建/更新知识库
                    with gr.Group(elem_id="create_kb_group"):
                        gr.Markdown("## ➕ 添加/更新知识库")
                        kb_name = gr.Textbox(
                            label="知识库名称", 
                            placeholder="请输入知识库名称，例如：产品手册", 
                            elem_id="kb_name_input"
                        )
                        
                        # 文件上传区
                        kb_files = gr.File(
                            label="上传文档", 
                            file_count="multiple", 
                            file_types=[".txt", ".pdf", ".doc", ".docx", ".md"],
                            elem_id="kb_files_upload"
                        )
                        
                        # 创建按钮使用一个单独的行，让它居中且更大
                        with gr.Row(elem_id="create_btn_row"):
                            create_kb_btn = gr.Button(
                                "创建/更新知识库", 
                                variant="primary", 
                                size="lg",
                                min_width=200,
                                elem_id="create_kb_btn"
                            )
                    
                    # 删除知识库
                    with gr.Group(elem_id="delete_kb_group"):
                        gr.Markdown("## ❌ 删除知识库")
                        with gr.Row():
                            delete_kb_name = gr.Dropdown(
                                label="要删除的知识库名称",
                                choices=[],
                                value=None,
                                interactive=True,
                                scale=3,
                                elem_id="delete_kb_name"
                            )
                            delete_kb_btn = gr.Button(
                                "删除知识库", 
                                variant="primary", 
                                size="sm",
                                scale=1,
                                elem_id="delete_kb_btn"
                            )
                
                
                # 右侧状态和知识库列表
                with gr.Column(scale=2, elem_id="kb_status_column"):
                    # 操作状态
                    with gr.Group(elem_id="kb_status_group"):
                        kb_status = gr.Textbox(
                            label="操作状态", 
                            interactive=False, 
                            lines=3,
                            elem_id="kb_status_text"
                        )
                    
                    # 知识库列表显示
                    with gr.Group(elem_id="kb_list_group"):
                        kb_list = gr.Textbox(
                            label="知识库列表", 
                            interactive=False, 
                            lines=10,
                            elem_id="kb_list_text"
                        )
                    
                    # 知识库使用说明
                    with gr.Accordion("📖 使用说明", open=True, elem_id="kb_help_accordion"):
                        gr.Markdown("""
                        ### 知识库使用说明
                        
                        1. **创建知识库**：输入名称并上传文件，点击创建按钮
                        2. **更新知识库**：使用已存在的知识库名称，上传新文件
                        3. **删除知识库**：输入名称并点击删除按钮
                        
                        支持的文件格式：TXT、PDF、DOC、DOCX、MD
                        """)
            


            # 绑定知识库管理功能
            create_kb_btn.click(
                create_or_update_knowledge_base,
                inputs=[kb_files, kb_name],
                outputs=kb_status
            ).then(
                fn=init_knowledge_bases,
                outputs=[kb_name_dropdown, delete_kb_name, kb_list]
            )
            
            delete_kb_btn.click(
                delete_knowledge_base,
                inputs=[delete_kb_name],
                outputs=kb_status
            ).then(
                fn=init_knowledge_bases,
                outputs=[kb_name_dropdown, delete_kb_name, kb_list]
            )
            


    chat_tab.select(
        fn=refresh_knowledge_bases,  
        outputs=kb_name_dropdown
    )
    
    kb_tab.select(
        fn=refresh_knowledge_bases,
        outputs=delete_kb_name
    )

    app.load(
        fn=init_knowledge_bases,
        outputs=[kb_name_dropdown, delete_kb_name, kb_list],
        queue=False
    )


if __name__ == "__main__":
    # 启动Gradio应用
    app.launch(
        share=False,
        server_name="0.0.0.0",
        server_port=7860,
    )