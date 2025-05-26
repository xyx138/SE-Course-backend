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
from agent import Agent
from retrieve import Retriever
from vectorStore import VectorStore
from requirements_agent import RequirementsAnalysis

# 加载环境变量
load_dotenv()

PROJECT_PATH = os.getenv("PROJECT_PATH")

examples = [
    "爬取豆瓣评分前10的电影，并写入到movies.txt文件中？",
    "从北京到天津的路径规划？",
    "今天北京的天气怎么样？"
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

async def check_agent_status():
    """检查Agent状态"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/status")
            if response.status_code == 200:
                result = response.json()
                return result.get("status") == "ready"
    except Exception:
        return False
    return False

async def process_message(message, history):
    """处理聊天消息"""
    if not message or not message.strip():
        return "请输入有效的消息"
        
    print(f"处理消息: {message}")
    try:
        # 检查Agent状态
        if not await check_agent_status():
            return "Agent 尚未准备好，请稍后再试"
            
        # 发送消息
        response = await send_message_to_agent(message)
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

# 需求分析相关函数
async def analyze_requirements(message):
    """分析用户输入的需求"""
    try:
        api_url = "http://localhost:8000/analyze_requirements"
        data = {"message": message}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("analysis", "分析失败")
            else:
                return f"请求失败: {response.text}"
    except Exception as e:
        return f"分析需求时出错: {str(e)}"

async def generate_requirement_doc(requirements):
    """生成需求文档"""
    try:
        api_url = "http://localhost:8000/generate_requirement_doc"
        data = {"requirements": requirements}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("document", "生成文档失败")
            else:
                return f"请求失败: {response.text}"
    except Exception as e:
        return f"生成文档时出错: {str(e)}"

async def generate_use_case_diagram(requirements):
    """生成用例图"""
    try:
        api_url = "http://localhost:8000/generate_use_case_diagram"
        data = {"requirements": requirements}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("plantuml_code", ""), result.get("image_url", "")
            else:
                return "", f"请求失败: {response.text}"
    except Exception as e:
        return "", f"生成用例图时出错: {str(e)}"

# SRS模板字符串（可编辑）
SRS_DEFAULT_TEMPLATE = '''软件需求规格说明书（SRS）
项目名称：XXX系统
版本号：1.0
编写日期：YYYY-MM-DD

1. 引言
1.1 目的
说明本文档的目标，例如：
定义XXX系统的功能和非功能性需求，作为开发团队、客户和利益相关者的参考依据。

1.2 范围
描述系统的边界和覆盖范围，例如：
本系统是一个基于Web的在线考试平台，支持教师创建试题、学生在线答题、自动评分和成绩分析功能。

1.3 读者对象
列出文档的目标读者，例如：
开发团队
项目管理者
客户/教师（课程评审）

2. 项目概述
2.1 背景
说明项目的背景和动机，例如：
传统纸质考试效率低下，需通过在线系统提升管理效率。

2.2 目标
列出项目的核心目标，例如：
实现试题的数字化管理
支持自动评分和成绩导出
提供实时考试监控

2.3 用户角色
定义系统的主要用户角色及其职责，例如：
角色\t描述
学生\t参与考试，查看成绩
教师\t创建试题、管理考试
管理员\t维护系统用户和权限
3. 用户需求
3.1 用户故事
以用户视角描述需求（格式：角色 + 需求 + 理由），例如：
用户故事1：作为教师，我希望能够批量导入试题，以节省手动输入时间。
用户故事2：作为学生，我希望在考试结束后立即查看成绩，以便了解学习情况。

3.2 用例图（可选）
附上用例图（或文字描述），例如：
用例：创建考试
参与者：教师
流程：登录 → 选择试题 → 设置考试时间 → 发布考试

4. 系统功能需求
4.1 功能模块划分
按模块分类功能需求，例如：

4.1.1 用户管理模块
功能1：用户注册与登录
输入：邮箱、密码
处理：验证信息并分配角色权限
输出：登录成功/失败提示

4.1.2 考试管理模块
功能1：创建考试
输入：试题列表、考试时间
处理：生成唯一考试链接
输出：考试ID和链接

5. 非功能性需求
5.1 性能需求
系统需支持500人同时在线考试，响应时间低于2秒。

5.2 安全性需求
用户密码需加密存储（如SHA-256）。
考试期间禁止学生切换浏览器标签页。

5.3 兼容性需求
支持Chrome、Firefox、Edge最新版本浏览器。

5.4 可靠性
系统故障后需在10分钟内恢复数据。

6. 项目约束
技术栈：必须使用Java Spring Boot + MySQL。
时间限制：需在学期结束前完成交付。
硬件限制：仅能使用学校提供的服务器资源。

7. 风险分析
风险\t可能性\t影响\t应对措施
服务器带宽不足\t中\t高\t增加负载均衡
第三方支付接口故障\t低\t中\t提供备用方案
8. 验收标准
所有用户故事均通过测试用例验证。
系统界面符合原型设计。
性能测试满足500并发用户需求。

9. 附录
9.1 参考资料
《软件工程实践指南》
类似系统竞品分析报告

9.2 术语表
SRS：软件需求规格说明书
并发用户数：同时在线操作的用户数量
'''

# 新增SRS文档生成函数
async def generate_srs_with_template(user_input, clarify_history, template):
    api_url = "http://localhost:8000/generate_srs_with_template"
    data = {
        "user_input": user_input,
        "clarify_history": clarify_history,
        "template": template
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json=data)
        if response.status_code == 200:
            result = response.json()
            return result.get("srs", "生成SRS文档失败")
        else:
            return f"请求失败: {response.text}"

def create_requirements_interface():
    """创建需求分析界面"""
    with gr.Blocks() as requirements_interface:
        gr.Markdown("# 需求分析智能体")

        # 1. 需求输入区
        with gr.Row():
            requirements_input = gr.Textbox(
                label="请输入您的需求",
                placeholder="请详细描述您的需求...",
                lines=5
            )
            analyze_btn = gr.Button("分析需求")

        # 2. 澄清对话区（紧跟需求输入区）
        clarify_history_state = gr.State([])
        with gr.Row():
            with gr.Column():
                clarify_chatbot = gr.Chatbot(label="澄清对话", height=300)
                clarify_input = gr.Textbox(label="补充/回答", placeholder="请输入对澄清问题的回答")
                clarify_btn = gr.Button("发送")

        # 3. SRS模板与生成区（放在澄清对话区下方）
        with gr.Row():
            with gr.Column():
                srs_template = gr.Textbox(label="SRS模板", value=SRS_DEFAULT_TEMPLATE, lines=20)
                generate_srs_btn = gr.Button("根据模板生成SRS文档")
                srs_output = gr.Markdown(label="SRS文档")

        # 4. 需求分析结果与文档/用例图生成区
        with gr.Row():
            with gr.Column():
                analysis_output = gr.JSON(label="需求分析结果")
                generate_doc_btn = gr.Button("生成需求文档")
                doc_output = gr.Markdown(label="需求文档")
            with gr.Column():
                generate_diagram_btn = gr.Button("生成用例图")
                diagram_code = gr.Textbox(label="PlantUML代码", lines=5)
                diagram_image = gr.Image(label="用例图")

        # 事件绑定
        analyze_btn.click(
            fn=analyze_requirements,
            inputs=requirements_input,
            outputs=analysis_output
        )
        generate_doc_btn.click(
            fn=generate_requirement_doc,
            inputs=analysis_output,
            outputs=doc_output
        )
        generate_diagram_btn.click(
            fn=generate_use_case_diagram,
            inputs=analysis_output,
            outputs=[diagram_code, diagram_image]
        )
        generate_srs_btn.click(
            fn=generate_srs_with_template,
            inputs=[requirements_input, clarify_history_state, srs_template],
            outputs=srs_output
        )
        clarify_btn.click(
            fn=clarify_interaction,
            inputs=[clarify_input, clarify_history_state, requirements_input],
            outputs=[clarify_chatbot, clarify_input, clarify_history_state]
        )
        # 用户输入需求后自动触发澄清追问
        requirements_input.submit(
            fn=clarify_interaction,
            inputs=[gr.State("") , clarify_history_state, requirements_input],
            outputs=[clarify_chatbot, clarify_input, clarify_history_state]
        )
    return requirements_interface

def create_interface():
    """创建主界面"""
    with gr.Blocks() as demo:
        gr.Markdown("# 智能问答系统")
        
        with gr.Tabs() as tabs:
            with gr.TabItem("智能问答"):
                # 原有的问答界面代码
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
                    gr.Markdown("# 智能 Agent 助手", elem_id="title")
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

            with gr.TabItem("需求分析"):
                requirements_interface = create_requirements_interface()
                
    return demo

# 用户点击"发送"时，追加用户输入到历史，并调用clarify接口获得LLM追问
async def clarify_interaction(user_input, history, requirements_input):
    # 如果是自动触发（user_input为空），只让LLM先问第一个问题
    if not user_input:
        api_url = "http://localhost:8000/clarify_requirement"
        data = {
            "user_input": requirements_input,
            "history": history
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=data)
            if response.status_code == 200:
                clarify = response.json().get("clarify", "")
                history = history + [{"role": "assistant", "content": clarify}]
                return history, "", history
            else:
                return history, "", history
    # 正常用户补充
    history = history + [{"role": "user", "content": user_input}]
    api_url = "http://localhost:8000/clarify_requirement"
    data = {
        "user_input": requirements_input,
        "history": history
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json=data)
        if response.status_code == 200:
            clarify = response.json().get("clarify", "")
            history = history + [{"role": "assistant", "content": clarify}]
            return history, "", history
        else:
            return history, "", history

if __name__ == "__main__":
    demo = create_interface()
    demo.launch(share=False)