import os
import asyncio
import threading
import gradio as gr
from dotenv import load_dotenv
import time
from pathlib import Path
import json
import shutil

# 导入你的 Agent 相关模块
from agent import Agent
from retrieve import Retriever
from vectorStore import VectorStore

# 加载环境变量
load_dotenv()
api_key = os.getenv("DASHSCOPE_API_KEY")
base_url = os.getenv("DASHSCOPE_BASE_URL")
model = 'qwen-plus'

# 确保必要的目录存在
KNOWLEDGE_DIR = os.path.join(os.getenv("PROJECT_PATH"), "knowledge_base")
VECTOR_STORE_DIR = os.path.join(os.getenv("PROJECT_PATH"), "VectorStore")

PROJECT_ROOT = os.getenv("PROJECT_PATH")

os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

# 全局变量
agent = None
agent_lock = threading.Lock()
agent_ready = threading.Event()
retriever = Retriever(similarity_threshold=0.7)

# 在全局范围创建事件循环
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)



# 启动 Agent 的异步任务
async def start_agent():
    global agent
    try:
        agent = Agent(api_key, base_url, model)
        await agent.setup()
        agent_ready.set()
        print("Agent 初始化完成")
    except Exception as e:
        print(f"Agent 初始化失败: {e}")
        agent = None

# 在后台线程中启动 Agent
def background_start_agent():
    global loop
    loop.run_until_complete(start_agent())

# 发送消息给 Agent 并获取回复
# 发送消息给 Agent 并获取回复
async def send_message_to_agent(message):
    if not agent or not agent_ready.is_set():
        return "Agent 尚未准备好，请稍后再试"
        
    try:    
        # 调用 Agent 并确保返回非 None 值
        if hasattr(agent, 'chat'):
            response = await agent.chat(message)
            # 检查并处理返回值类型
            if response is None:
                return "Agent 返回了空回复"
            elif isinstance(response, str):
                return response
            else:
                # 尝试将非字符串类型转换为字符串
                try:
                    return str(response)
                except:
                    return "无法处理 Agent 返回的非字符串格式回复"
        else:
            return "Agent 对象没有 chat 方法"
            
    except Exception as e:
        print(f"处理消息时出错: {e}")
        return f"处理消息时出错: {str(e)}"

# 创建或更新知识库
async def create_or_update_knowledge_base(files, name):
    if not name:
        return "请提供知识库名称"
    
    # 创建知识库目录
    kb_dir = os.path.join(KNOWLEDGE_DIR, name)
    os.makedirs(kb_dir, exist_ok=True)
    
    # 保存上传的文件
    file_paths = []
    for file in files:
        dest_path = os.path.join(kb_dir, os.path.basename(file.name))
        shutil.copy(file.name, dest_path)
        file_paths.append(dest_path)
    
    # 创建向量存储
    try:
        # vector_store = VectorStore(index_path=VECTOR_STORE_DIR)
        # vector_store.create_index(file_path=kb_dir, label=name)
        await agent.create_index(files_dir=kb_dir, label=name)
        return f"成功创建/更新知识库: {name}，包含 {len(file_paths)} 个文件"
    except Exception as e:
        return f"创建向量存储时出错: {str(e)}"

# 删除知识库
def delete_knowledge_base(name):
    if not name:
        return "请提供知识库名称"
    
    kb_dir = os.path.join(KNOWLEDGE_DIR, name)
    vs_dir = os.path.join(VECTOR_STORE_DIR, name)
    
    result = []
    
    # 删除知识库文件
    if os.path.exists(kb_dir):
        try:
            shutil.rmtree(kb_dir)
            result.append(f"已删除知识库文件夹: {kb_dir}")
        except Exception as e:
            result.append(f"删除知识库文件夹失败: {str(e)}")
    
    # 删除向量存储
    if os.path.exists(vs_dir):
        try:
            shutil.rmtree(vs_dir)
            result.append(f"已删除向量存储: {vs_dir}")
        except Exception as e:
            result.append(f"删除向量存储失败: {str(e)}")
    
    if not result:
        return f"未找到知识库: {name}"
    
    return "\n".join(result)

# 列出所有知识库
def list_knowledge_bases():
    kbs = os.listdir(KNOWLEDGE_DIR) if os.path.exists(KNOWLEDGE_DIR) else []
    if not kbs:
        return "没有找到知识库"
    
    return kbs


# 修改处理聊天消息的函数
def process_message(message, history):
    if not message or not message.strip():
        return "请输入有效的消息"
        
    print(f"处理消息: {message}")
    try:
        response = loop.run_until_complete(send_message_to_agent(message))
        print(f"收到回复: {response[:100]}...")
        return response
    except Exception as e:
        print(f"处理消息时出错: {e}")
        return f"处理消息时出错: {str(e)}"

# 选择知识库
def select_knowledge_base(kb_name):
    global agent
    if agent:
        response = loop.run_until_complete( agent.update_label(kb_name) )
    return f"选择知识库：{kb_name}"


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
        with gr.TabItem("💬 聊天", id="chat_tab"):
            # 主要内容区域
            with gr.Row(equal_height=True):
                # 左侧聊天区域 (占据更多空间)
                with gr.Column(scale=5, elem_id="chat_column"):
                    # 聊天记录
                    chatbot = gr.Chatbot(
                        height=600, 
                        type="messages",
                        avatar_images=(f"{PROJECT_ROOT}/images/user.png", 
                                     f"{PROJECT_ROOT}/images/bot.jpg"),
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
                            scale=5
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
                            kb_name = gr.Dropdown(
                                label="当前知识库",
                                choices=list_knowledge_bases(),
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
                        example_btn1 = gr.Button("帮我爬取豆瓣评分前10的电影", size="sm", elem_id="example1")
                        example_btn2 = gr.Button("当前项目包含哪些目录文件", size="sm", elem_id="example2")
                        example_btn3 = gr.Button("从北京科技大学到天安门的路线规划", size="sm", elem_id="example3")

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
                
            example_btn1.click(use_example, [gr.State("什么是机器学习?")], [msg])
            example_btn2.click(use_example, [gr.State("帮我整理一份周报")], [msg])
            example_btn3.click(use_example, [gr.State("如何使用知识库?")], [msg])
            
            # 消息处理功能
            def user_message(user_message, history):
                if not user_message:
                    return "", history
                return "", history + [{"role": "user", "content": user_message}]
            
            def bot_message(history):
                try:
                    user_message = history[-1]["content"]
                    bot_message = process_message(user_message, history[:-1])
                    return history + [{"role": "assistant", "content": bot_message}]
                except Exception as e:
                    print(f"处理消息时出错: {e}")
                    return history + [{"role": "assistant", "content": f"处理消息时出错: {str(e)}"}]
            
            # 清空聊天
            def clear_chat():
                return None
            
            # 绑定事件
            msg.submit(user_message, [msg, chatbot], [msg, chatbot], queue=False).then(
                bot_message, chatbot, chatbot
            )
            
            send_btn.click(user_message, [msg, chatbot], [msg, chatbot], queue=False).then(
                bot_message, chatbot, chatbot
            )
            
            clear_btn.click(clear_chat, None, chatbot, queue=False)
            
            select_kb_btn.click(select_knowledge_base, [kb_name], [system_status])

        # 知识库管理标签页 - 美化版
        with gr.TabItem("📚 知识库管理", id="kb_tab"):
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
                                choices=list_knowledge_bases(),
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
                    
                    # 知识库列表
                    with gr.Group(elem_id="list_kb_group"):
                        gr.Markdown("## 📋 知识库列表")
                        list_kb_btn = gr.Button(
                            "刷新知识库列表", 
                            size="sm", 
                            elem_id="list_kb_btn"
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
                            placeholder="点击「刷新知识库列表」按钮查看所有知识库",
                            elem_id="kb_list_text"
                        )
                    
                    # 知识库使用说明
                    with gr.Accordion("📖 使用说明", open=True, elem_id="kb_help_accordion"):
                        gr.Markdown("""
                        ### 知识库使用说明
                        
                        1. **创建知识库**：输入名称并上传文件，点击创建按钮
                        2. **更新知识库**：使用已存在的知识库名称，上传新文件
                        3. **删除知识库**：输入名称并点击删除按钮
                        4. **查看列表**：点击刷新按钮查看所有知识库
                        
                        支持的文件格式：TXT、PDF、DOC、DOCX、MD
                        """)
            
            # 绑定知识库管理功能
            create_kb_btn.click(
                lambda x, y: loop.run_until_complete(create_or_update_knowledge_base(x, y)),
                inputs=[kb_files, kb_name],
                outputs=kb_status
            )
            
            delete_kb_btn.click(
                delete_knowledge_base,
                inputs=[delete_kb_name],
                outputs=kb_status
            )
            
            list_kb_btn.click(
                list_knowledge_bases,
                inputs=[],
                outputs=kb_list
    )


if __name__ == "__main__":
    # 启动Agent线程
    threading.Thread(target=background_start_agent, daemon=True).start()
    
    # 等待agent初始化
    time.sleep(2)
    
    # 启动Gradio应用
    app.launch(
        share=False,
        server_name="0.0.0.0",
        server_port=7860,
    )