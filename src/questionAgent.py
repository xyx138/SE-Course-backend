from llmClient import LLMClient
from mcpClient import MCPClient

from utils.load_json import load_mcp_config
from utils.logger import MyLogger, logging
from collections import defaultdict
from dotenv import load_dotenv
import os
import asyncio
import sys
from asyncio import CancelledError
import json
from retrieve import Retriever
import time 
import traceback
import random
# import aiomysql

load_dotenv()

PROJECT_PATH = os.getenv('PROJECT_PATH')

logger = MyLogger(log_file="logs/app.log", level=logging.INFO)
# 数据库配置/用户答题记录
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "你的用户名",
    "password": "你的密码",
    "db": "chatbot"
}

class questionAgent():
    '''agent = llm+tool'''
    
    def __init__(self, api_key:str , base_url:str , model: str = None, label: str = '习题库') -> None:
        '''初始化 llm 客户端和 mcp 客户端'''

        logger.info("初始化LLM和MCP客户端")

        system_prompt = f'''你是一个软件工程习题辅导专家，请严格按照以下规则进行引导：
                1. 当我让你给我出一道题时，你默认从习题库中去寻找习题，并且不用分步引导，直接给出一道题。
                2. 当用户提问涉及具体题目时，按以下流程处理：
                    a. 分析题目类型和知识点
                    b. 参考相似题目解答模式
                    c. 生成引导式提问
                3. 禁止直接给出完整答案或代码
                4. 当检测到知识盲点时，提示相关基础概念
                5. 使用中文进行交流，保持专业且友好的语气必要的时候，你可以直接调用工具来实现用户的需求。
  
               
                '''
        self.llmClient = LLMClient(api_key, base_url, model, system_prompt=system_prompt)
        
        
        mcp_servers = load_mcp_config(PROJECT_PATH + '/mcp.json')['mcpServers']
        self.mcp_clients = defaultdict(MCPClient)
        self.tools = []
        for server_name, config in mcp_servers.items():
            command, args = config['command'], config['args']
            self.mcp_clients[server_name] = MCPClient(command, args)

        self.retriever = Retriever(similarity_threshold=0.5)
        self.label = label
        self.error_history = []  # 存储错误历史
        self.knowledge_points = {}  # 存储知识点掌握情况
        self.answer_history = []  # 新增

    async def update_label(self, label: str):
        '''
        更新索引标签

        args:
            label: 索引标签
        '''

        self.label = label
        print(f"成功挂载知识库：{self.label}")

    async def write_messages(self):
        '''
        把上下文写入到文件
        '''

        all_text = [f"{message['role']}: {message['content']}" for message in self.llmClient.messages]
        all_text = '\n'.join(all_text)

        log_messages_dir = f"{PROJECT_PATH}/logs"
        os.makedirs(log_messages_dir, exist_ok=True)
        log_messages_file = f"{log_messages_dir}/messages.json"
        with open(log_messages_file, "w") as f:
            f.write(all_text)
            

    async def setup(self):
        # 启动所有服务，并记录所有工具

        logger.info("启动MCP服务器")

        try:
            for name in self.mcp_clients:
                mcp_client = self.mcp_clients[name]
                await mcp_client.connect_to_server()
            
            
            for name, client in self.mcp_clients.items():
                tools = client.getTool()
                # print(f"获取到的工具为：{tools}")
                self.tools.extend([
                    {
                        "type": "function",

                        "function":{
                        "name" : tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                        } 
                    }
                
                for tool in tools])
            print(f"获取到的工具数为：{len(self.tools)}")

        except Exception as e:
            # 异常处理代码
            print(f"发生错误: {e}")
            # 可能的恢复策略
    
    async def chat(self, query: str) -> str:
        try:
            logger.info(f"开始检索")
            print(f"检索的标签为：{self.label}")
            chunk_text = self.retriever.retrieve(query, self.label)
            print(f"检索结果为：{chunk_text}")

            prompt = f"根据以下检索结果，回答用户的问题：\n{chunk_text}\n用户的问题是：{query}"

            logger.info(f"调用LLM")
            res = await self.llmClient.chat(prompt, self.tools)
            
            tool_calls = res.choices[0].message.tool_calls

            while tool_calls:
                logger.info("调用工具")
                tool_names = [tool.function.name for tool in tool_calls]

                print(f"调用的工具包括：{tool_names}")
                # 确保工具调用在主线程中执行
                for tool_call in tool_calls:
                    func = tool_call.function
                    name, args = func.name, func.arguments
                    logger.info(f"调用工具:{name}")
                    
                    args = json.loads(args)
                    target_client = None
                    for mcp_name, mcp_client in self.mcp_clients.items():
                        if mcp_client.have_tool(name):
                            target_client = mcp_client
                            print(f"找到{name}对应的mcp_client:{target_client}")
                            break
                    
                    if target_client:
                        print(f"调用{name}，参数为{args}")
                        try:
                            # 检查客户端连接状态，如果需要则重新连接
                            if not target_client._connected or target_client.session is None:
                                logger.warning(f"检测到客户端未连接或会话为空，尝试重新连接")
                                await target_client.connect_to_server()
                                
                            # 调用工具
                            tool_res = await target_client.call_tool(name, args)  
                            print(f"调用{name}的执行结果为{tool_res}")
                            await self.llmClient.add_tool_call(
                                role="tool", 
                                content=tool_res.content, 
                                tool_call_id=tool_call.id
                            )
                        except Exception as e:
                            print(f"工具{name}调用出错: {e}")
                            # 如果是事件循环关闭错误，尝试重新连接所有客户端
                            if "Event loop is closed" in str(e):
                                print("检测到事件循环关闭错误，尝试重新连接所有客户端")
                                try:
                                    await self.reconnect_all_clients()
                                    # 重试工具调用
                                    try:
                                        tool_res = await target_client.call_tool(name, args)
                                        print(f"重新连接后调用{name}的执行结果为{tool_res}")
                                        await self.llmClient.add_tool_call(
                                            role="tool", 
                                            content=tool_res.content, 
                                            tool_call_id=tool_call.id
                                        )
                                    except Exception as retry_e:
                                        print(f"重试调用工具{name}失败: {retry_e}")
                                        await self.llmClient.add_tool_call(
                                            role="tool", 
                                            content=f"工具{name}调用出错: {str(retry_e)}", 
                                            tool_call_id=tool_call.id
                                        )
                                except Exception as reconnect_e:
                                    print(f"重新连接客户端失败: {reconnect_e}")
                                    await self.llmClient.add_tool_call(
                                        role="tool", 
                                        content=f"工具{name}调用出错: 事件循环已关闭且无法重新连接 - {str(e)}", 
                                        tool_call_id=tool_call.id
                                    )
                            else:
                                await self.llmClient.add_tool_call(
                                    role="tool", 
                                    content=f"工具{name}调用出错: {str(e)}", 
                                    tool_call_id=tool_call.id
                                )

                res = await self.llmClient.chat(message=None, tools=self.tools)
                tool_calls = res.choices[0].message.tool_calls if res.choices[0].message.tool_calls else None
            
            logger.info("回复结果")
            await self.write_messages() # 写入上下文信息
            return res.choices[0].message.content
        except Exception as e:
            logger.error(f"聊天过程中出错: {e}")
            logger.error(traceback.format_exc())
            return f"处理请求时出错: {str(e)}"

    async def delete_index(self, label: str):
        res = self.retriever.delete_index(label)
        if res == 1:
            logger.info(f"删除向量索引成功，索引标签为{label}")
        else:
            logger.error(f"删除向量索引失败: {res}")


    async def create_index(self, files_dir: str, label: str):
        '''
        创建向量索引

        args:
            file_path: 文件路径
            label: 索引标签
        '''
        index = self.retriever.create_index(files_dir, label)
        logger.info(f"创建向量索引成功，索引标签为{label}")
        return index



    async def cleanup(self):
        """清理所有客户端资源，必须和 connect_to_server 在同一任务中执行"""
        for name, client in self.mcp_clients.items():
            try:
                # 直接 await，不要 shield，也不要并行 gather
                await client.cleanup()
                logger.info(f"客户端 {name} 清理完成")
            except Exception as e:
                logger.error(f"清理客户端 {name} 时出错: {e}")

    async def reconnect_all_clients(self):
        """尝试重新连接所有MCP客户端"""
        for name, client in self.mcp_clients.items():
            try:
                await client.connect_to_server()
                logger.info(f"重新连接客户端 {name} 成功")
            except Exception as e:
                logger.error(f"重新连接客户端 {name} 失败: {e}")
    async def get_one_question_by_knowledge_point(self, knowledge_point: str) -> dict:
        try:
            if not self.label:
                return {"error": "请先选择一个习题库"}
            result = self.retriever.retrieve_by_knowledge_point(knowledge_point, self.label)
            # 直接返回 result
            return result
        except Exception as e:
            logger.error(traceback.format_exc())
            return {"error": f'检索习题时出错: {str(e)}'}
    async def analyze_knowledge_points(self, query: str) -> dict:
        """分析用户查询中的知识点并检索相关习题"""
        try:
            # 检查是否已选择知识库
            if not self.label:
                return {
                    "error": "请先选择一个知识库",
        
                }

            # 使用LLM提取知识点
            template = f'''
            注意：你只需要回复以下json格式的内容：
                {{
                    "answer": "你的回复内容",
                    "knowledge_points": ["知识点1", "知识点2", "知识点3"]
                }}
            '''


            prompt = f"请给出与{query}相关的题目, {template}"

            res = await self.chat(prompt)
            print(f"question_agent_res:{res}")  
            # 提取知识点
            return res
        except Exception as e:
            logger.error(f"分析知识点时出错: {e}")
            return {"error": f"分析知识点时出错: {str(e)}"}


    async def track_error(self, question: str, user_answer: str, correct: bool):
        """记录用户答题情况"""
        try:
            # 提取题目中的知识点
            prompt = f"请从以下题目中提取关键知识点：{question}"
            res = await self.llmClient.chat(prompt)
            knowledge_points = res.choices[0].message.content.split(",")
            
            # 更新知识点掌握情况
            for point in knowledge_points:
                point = point.strip()
                if point:
                    if point not in self.knowledge_points:
                        self.knowledge_points[point] = {"correct": 0, "total": 0}
                    self.knowledge_points[point]["total"] += 1
                    if correct:
                        self.knowledge_points[point]["correct"] += 1
            
            # 记录错误历史
            if not correct:
                self.error_history.append({
                    "question": question,
                    "user_answer": user_answer,
                    "knowledge_points": knowledge_points,
                    "timestamp": time.time()
                })
            
            # 记录所有答题历史
            self.answer_history.append({
                "question": question,
                "user_answer": user_answer,
                "knowledge_points": knowledge_points,
                "correct": correct,
                "timestamp": time.time()
            })
            
            await self.save_conversation_to_mysql(
                question=question,
                answer=user_answer,
                knowledge_points=knowledge_points,
                correct=correct,
                user_id=None
            )
            
            return {"status": "success"}
        except Exception as e:
            logger.error(f"记录错误时出错: {e}")
            return {"error": str(e)}

    async def get_learning_analysis(self):
        """
        返回易错知识点和知识盲点分析
        """
        # 统计错题知识点
        error_points = []
        for err in self.error_history:
            error_points.extend(err.get("knowledge_points", []))
        # 统计出现频率
        from collections import Counter
        error_counter = Counter(error_points)
        # 取前N个易错知识点
        most_common_errors = error_counter.most_common(5)

        # 统计知识盲点（题库中有但用户从未答对过的知识点）
        all_points = set(self.retriever.get_all_knowledge_points())
        answered_points = set()
        for record in self.answer_history:  # 假设你有答题历史
            if record.get("correct"):
                answered_points.update(record.get("knowledge_points", []))
        blind_points = list(all_points - answered_points)

        return {
            "易错知识点": [{"知识点": k, "错误次数": v} for k, v in most_common_errors],
            "知识盲点": blind_points
        }

    async def step_by_step_solve(self, question: str) -> dict:
        try:
            if not self.label:
                return {"error": "请先选择一个知识库"}
            # 1. 检索相关知识点/相似题
            related_chunks = self.retriever.retrieve(question, self.label)
            # 2. 构造分步引导 prompt
            prompt = (
                "你是一名智能学习助手。请结合下方检索到的知识点和相似题，"
                "对用户输入的题目进行分步引导式解答。每一步都要详细说明思路，不要直接给出最终答案。\n\n"
                f"【检索到的知识/相似题】\n{related_chunks}\n"
                f"【用户题目】\n{question}\n"
                "请按以下格式输出：\n"
                "第1步：...\n第2步：...\n（直到解题完成）"
            )
            # 3. 调用大模型
            res = await self.llmClient.chat(prompt)
            answer = res.choices[0].message.content
            return {"step_by_step_solution": answer}
        except Exception as e:
            return {"error": f"分步解题时出错: {str(e)}"}

    # async def save_conversation_to_mysql(self, question, answer, knowledge_points=None, correct=None, user_id=None):
    #     try:
    #         conn = await aiomysql.connect(
    #             host=MYSQL_CONFIG["host"],
    #             port=MYSQL_CONFIG["port"],
    #             user=MYSQL_CONFIG["user"],
    #             password=MYSQL_CONFIG["password"],
    #             db=MYSQL_CONFIG["db"],
    #             autocommit=True
    #         )
    #         async with conn.cursor() as cur:
    #             await cur.execute(
    #                 "INSERT INTO conversation_history (user_id, question, answer, knowledge_points, correct) VALUES (%s, %s, %s, %s, %s)",
    #                 (user_id, question, answer, ','.join(knowledge_points) if knowledge_points else None, correct)
    #             )
    #         conn.close()
    #     except Exception as e:
    #         logger.error(f"MySQL写入对话历史失败: {e}")



            


api_key = os.getenv("DASHSCOPE_API_KEY")
base_url = os.getenv("DASHSCOPE_BASE_URL")
model = 'qwen-plus'

async def main():
    agent = questionAgent(api_key, base_url, model)
    await agent.setup()
    # 这里可以添加更多使用 agent 的代码
    res = await agent.chat("你可以操作哪一个文件夹？")
    print(f"回复结果为：{res}")
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"程序运行时出错: {e}")