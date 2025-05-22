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

# 加载环境变量
load_dotenv()

PROJECT_PATH = os.getenv("PROJECT_PATH")

examples = [
    "给我出一道考察数据流程图的习题",
    "总结我的知识盲点",
    "如何证明贪心算法的最优子结构性质？"
]

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
    """
) as app:   
    gr.Markdown("# 🤖 智能 Agent 助手", elem_id="title")
    gr.Markdown("### 基于大型语言模型和知识库的智能问答系统", elem_id="subtitle") 
    
    with gr.Tabs() as tabs:
        # 聊天标签页 - 美化版
        with gr.TabItem("💬 聊天", id="chat_tab") as chat_tab:
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



        # 知识库管理标签页 - 美化版 
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
    with gr.TabItem("🎯 知识点出题", id="one_question_tab"):
        with gr.Row():
            knowledge_point_input = gr.Textbox(
                label="输入知识点",
                placeholder="如：数据流程图",
                lines=1
            )
            get_question_btn = gr.Button("随机出一道题", variant="primary")
        question_output = gr.Textbox(label="习题内容", lines=8, interactive=False)

        async def get_one_question(knowledge_point):
            if not knowledge_point.strip():
                return "请输入知识点"
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        "http://localhost:8000/one_question_by_knowledge_point",
                        params={"knowledge_point": knowledge_point}
                    )
                    data = resp.json()
                    # 兼容 questions 列表
                    if "questions" in data and isinstance(data["questions"], list) and len(data["questions"]) > 0:
                        # 只取第一道题
                        return data["questions"][0]["question"]
                    elif "question" in data:
                        return data["question"]
                    elif "error" in data:
                        return data["error"]
                    else:
                        return "未获取到题目"
            except Exception as e:
                return f"请求出错: {str(e)}"

    get_question_btn.click(
        get_one_question,
        inputs=[knowledge_point_input],
        outputs=[question_output]
    )
    # 学习分析标签页 - 新增
    with gr.TabItem("📊 学习分析", id="learning_tab") as learning_tab:
        with gr.Row():
            analysis_btn = gr.Button("生成易错知识点与知识盲点分析", variant="primary")
            analysis_results = gr.JSON(label="分析报告")

        async def get_learning_analysis():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://localhost:8000/learning_analysis")
                    return response.json().get("data", {})
            except Exception as e:
                return {"error": str(e)}

        analysis_btn.click(
            get_learning_analysis,
            inputs=[],
            outputs=[analysis_results]
        )

    # 新增分步交互解题Tab
    with gr.Tab("📝分步交互解题"):
        gr.Markdown("#### 分步交互式引导解题")
        question_input = gr.Textbox(label="请输入你要解答的题目", lines=4)
        history_state = gr.State([])  # 存储历史对话
        history_output = gr.Markdown(label="对话历史")
        current_step_output = gr.Markdown(label="当前引导")
        user_reply = gr.Textbox(label="你的本步回答", lines=2)
        start_btn = gr.Button("开始分步解题")
        next_btn = gr.Button("提交本步回答")

        # 格式化历史
        def format_history(history):
            return "\n\n".join(
                [f"**{'学生' if h['role']=='user' else '老师'}：** {h['content']}" for h in history]
            )

        # 1. 开始分步解题，自动请求第1步
        async def start_step_by_step(question):
            history = []
            # 请求第1步引导
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "http://localhost:8000/step_by_step_interactive",
                    json={"question": question, "history": history}
                )
                data = resp.json()
                if "step" in data:
                    step = data["step"]
                    history.append({"role": "assistant", "content": step})
                    return history, format_history(history), step, ""
                else:
                    return history, "", "未获取到第1步引导", ""

        start_btn.click(
            start_step_by_step,
            inputs=question_input,
            outputs=[history_state, history_output, current_step_output, user_reply]
        )

        # 2. 交互式每一步
        async def interactive_step(question, history, user_reply_text):
            history = list(history)
            if user_reply_text.strip():
                history.append({"role": "user", "content": user_reply_text})
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "http://localhost:8000/step_by_step_interactive",
                    json={"question": question, "history": history}
                )
                data = resp.json()
                if "history" in data:
                    finished = data.get("finished", False)
                    # 如果 finished，禁用输入框和按钮
                    if finished:
                        return (
                            data["history"],
                            format_history(data["history"]),
                            "🎉 本题已完成！",
                            gr.update(value="", interactive=False),  # 禁用输入框
                            gr.update(interactive=False)             # 禁用按钮
                        )
                    else:
                        return (
                            data["history"],
                            format_history(data["history"]),
                            "",  # 当前引导区留空
                            gr.update(value="", interactive=True),   # 输入框可用
                            gr.update(interactive=True)              # 按钮可用
                        )
                else:
                    return history, format_history(history), "未获取到下一步引导", gr.update(interactive=True), gr.update(interactive=True)

        # 绑定时，outputs 多加一个 user_reply 和 next_btn
        next_btn.click(
            interactive_step,
            inputs=[question_input, history_state, user_reply],
            outputs=[history_state, history_output, current_step_output, user_reply, next_btn]
        )
if __name__ == "__main__":
    # 启动Gradio应用
    app.launch(
        share=False,
        server_name="0.0.0.0",
        server_port=7860,
    )