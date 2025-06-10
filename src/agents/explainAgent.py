from agents.agent import Agent
from dotenv import load_dotenv
import os
import asyncio
import json
load_dotenv()

'''
概念解释agent

'''

class ExplainAgent(Agent):
    def __init__(self, api_key: str, base_url: str, model: str = None, label: str = None) -> None:
        super().__init__(api_key, base_url, model, label, [
            'filesystem',
            'bingcn',
            # 'memory',
        ])
        self.output_dir = os.path.join(os.getenv('PROJECT_PATH'), 'static', 'docs')

    def get_system_prompt(self) -> str:
        base_prompt = super().get_base_system_prompt()
        explain_prompt = '''
            你是一个专业的概念解释助手，你的主要职责是：
            1. 准确理解用户需要解释的概念
            2. 根据不同的解释风格提供相应的解释
            3. 你只需要告诉用户对概念的解释，不要输出和解释无关的内容，例如，"已成功保存文件到xxx"
        '''
        return base_prompt + '\n' + explain_prompt


    async def chat(self, query: str, style: str,  bing_search: bool = False) -> str:
        # 将style转换为解释风格
        s2p = {
            'CONCISE': '用简洁明了的方式，给出要点式的解释。',
            'STRICT': '从专业严谨的角度，给出详细的解释，包含定义、特点、应用等方面。',
            'PROFESSIONAL': '使用专业术语和学术语言，从理论和实践两个层面进行深入解释。',
            'POPULAR': '用生动易懂的语言和具体的例子，从日常生活的角度进行解释。',
            'FUNNY': '用轻松幽默的方式，通过有趣的比喻和例子来解释概念。'
        }


        prompt = f"""
        用户的问题是：{query},
        请用{s2p[style]}的风格解释这个概念。\n
        请使用bing_cn工具搜索，获取和用户的问题`{query}`相关的链接。 \n
        """

        
        prompt += f"""
        你只需要返回一个json字符串，包含以下内容：
        {{
            "message": "解释内容",
            "search_results": [
                {{
                    "title": "标题",
                    "link": "链接"
                }},
                {{
                    "title": "标题",
                    "link": "链接"
                }}
            ]
        }}
        """

        # # 打印函数的参数
        # print("chat 参数")
        # print(f"query: {query}")
        # print(f"style: {style}")
        # print(f"output_file_name: {output_file_name}")
        # print(f"bing_search: {bing_search}")

        try:
            res = await super().chat(prompt) 

            if res['status'] == 'success':
                return res

            else:
                return {
                    "status": "error",
                    "message": res['message']
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"解释时出错: {str(e)}"
            }


async def main():
    api_key = os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv("DASHSCOPE_BASE_URL")
    model = 'qwen-plus'



    agent = ExplainAgent(api_key, base_url, model)
    await agent.setup()
    res = await(agent.chat("什么是人工智能？", "popular", "什么是人工智能.md", True))
    
    json_res = res['search_results']

    print(f"main res: {json_res}")

    obj_res = json.loads(json_res)
    print()
    print(obj_res)

    with open( os.path.join(os.getenv('PROJECT_PATH'), 'output', 'search_results.log'), 'w') as f:
        print("写入文件")
        f.write(obj_res)


if __name__ == "__main__":
    asyncio.run(main())