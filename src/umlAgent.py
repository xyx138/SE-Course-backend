from agent import Agent
from utils.logger import MyLogger, logging
import os
logger = MyLogger( level=logging.INFO)
from dotenv import load_dotenv

load_dotenv()

PROJECT_PATH = os.getenv("PROJECT_PATH")

class UML_Agent(Agent):
    def __init__(self, api_key: str, base_url: str, model: str, label: str = None):
       
        super().__init__(api_key, base_url, model, label)

    def get_system_prompt(self) -> str:
        system_prompt = f'''
        你是一个UML图生成专家，请根据用户的需求生成UML图。
        对于写文件，你的权限目录是：{os.path.join(PROJECT_PATH, "static")}。
        你的最终回复不需要提供生成的UML图的链接或者代码，只需要输出你画的UML图的解释文本，而且要尽可能详细的解释。
        '''

        return super().get_base_system_prompt() + '\n' + system_prompt

    async def generate_uml(self, query: str, diagram_type: str):
        try:
            
            prompt = f'''
            用户的需求是：{query}，
            请根据用户的需求生成{diagram_type}
            '''
            
            res = await self.chat(prompt)
            
            return res 
        
        except Exception as e:
            logger.error(f"生成UML图时出错: {e}")
            return {
                "status": "error",
                "message": f"生成UML图时出错: {str(e)}"
            }
    
    async def getTargetFilePath(self, diagram_type: str) -> str  : # 获取目标图片
        static_dir = os.path.join(PROJECT_PATH, "static", f"{diagram_type}")

        if not os.path.exists(static_dir):
            return {
                "status": "error",
                "message": f"静态图片目录不存在: {static_dir}"
            }
        
        uml_files = os.listdir(static_dir)
        if not uml_files:
            return {
                "status": "error",
                "message": f"静态图片目录为空: {static_dir}"
            }
        
        target_dir = os.path.join(static_dir, diagram_type)
        if not os.path.exists(target_dir):
            return {
                "status": "error",
                "message": f"目标图片目录不存在: {target_dir}"
            }
        
        target_file = os.path.join(target_dir, "uml.png")
        if not os.path.exists(target_file):
            return {
                "status": "error",
                "message": f"目标图片文件不存在: {target_file}"
            }
        
        return {
            "status": "success",
            "message": f"目标图片文件存在: {target_file}"
        }

async def main():
    api_key = os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv("DASHSCOPE_BASE_URL")
    model = 'qwen-plus'
    uml_agent = UML_Agent(api_key=api_key, base_url=base_url, model=model)
    await uml_agent.setup()
    res = await uml_agent.generate_uml("生成一个图书管理系统的uml图", "class")
    print(res)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())