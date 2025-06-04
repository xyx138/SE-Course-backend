from typing import List
from agents.agent import Agent, all_servers
import asyncio

class PaperAgent(Agent):

    def __init__(self) -> None:
        
        super().__init__(mcp_servers = [
            'arxiv-mcp-server',
        ])

    def get_system_prompt(self) -> str:
        return """
        你是一个专为软件工程课程学生设计的学术论文助手，你可以帮助学生查找、获取、理解和应用软件工程领域的学术论文。你的主要职责是：

        1. 论文搜索与推荐：
           - 根据学生的研究主题或关键词搜索相关论文
           - 推荐软件工程各子领域的经典和前沿论文
           - 针对特定软件工程问题提供有针对性的论文推荐

        2. 论文内容解析与总结：
           - 提供论文的核心观点和主要贡献的简明总结
           - 解释论文中的复杂概念和专业术语
           - 分析论文的研究方法和实验设计

        3. 学习辅助功能：
           - 根据论文内容回答学生的问题
           - 将论文的理论知识与实际软件工程实践联系起来
           - 帮助学生理解如何将论文中的方法应用到他们的课程项目中

        4. 文献管理与组织：
           - 帮助学生组织已下载的论文
           - 根据主题对论文进行分类
           - 提供论文间的关联性分析

        使用以下工具来完成这些任务：
        - search_papers：搜索与特定主题相关的论文
        - download_paper：下载指定的论文
        - list_papers：列出已下载的论文
        - read_paper：阅读并分析论文内容

        在与学生互动时，应注重以下几点：
        1. 使用清晰、易懂的语言解释复杂的学术概念
        2. 强调论文的实际应用价值和与课程项目的关联
        3. 鼓励批判性思考，而不仅仅是接受论文结论
        4. 提供进一步学习的方向和资源建议
        """

    async def search_papers_by_topic(self, topic: str, max_results: int = 10):
        """
        根据主题搜索相关论文
        
        Args:
            topic: 搜索主题或关键词
            max_results: 返回结果数量上限
        
        Returns:
            论文列表及简短描述
        """
        prompt = f"""
        请使用search_papers工具搜索与"{topic}"相关的软件工程论文。
        搜索参数:
        - query: "{topic}"
        - max_results: {max_results}
        
        如果{topic}为中文，请将它翻译为英文后再调用工具。
        搜索完成后，请以表格形式整理论文信息，包括标题、作者、发表年份和简短摘要。
        然后，请推荐其中最相关的2-3篇论文，并简要说明为什么推荐这些论文。
        """
        return await self.chat(prompt)

    async def download_and_read_paper(self, paper_id: str):
        """
        下载并阅读指定的论文
        
        Args:
            paper_id: 论文ID
            
        Returns:
            论文分析结果
        """
        prompt = f"""
        请按照以下步骤操作：
        1. 首先使用download_paper工具下载ID为"{paper_id}"的论文
        2. 然后使用read_paper工具读取这篇论文的内容
        3. 最后，请提供以下分析：
           - 论文的核心观点和主要贡献
           - 研究方法和实验设计的评价
           - 论文的实际应用价值，特别是对软件工程实践的启示
           - 论文中的关键概念解释
        
        请使用清晰、易懂的语言，适合软件工程专业的学生理解。注意，工具中的论文id参数是'paper_id'，而不是'id'。
        """
        return await self.chat(prompt)

    async def list_and_organize_papers(self):
        """
        列出并组织已下载的论文
        
        Returns:
            已下载的论文列表及分类
        """
        prompt = """
        请使用list_papers工具列出所有已下载的论文，然后：
        1. 将论文按主题领域分类（如：软件架构、测试方法、项目管理等）
        2. 为每个主题领域的论文集合提供一个简短的概述
        3. 推荐一个合理的阅读顺序，从基础到高级
        
        请以清晰的结构呈现这些信息，便于学生理解和使用。
        """
        return await self.chat(prompt)
    
    async def analyze_paper_for_project(self, paper_id: str, project_description: str):
        """
        分析论文对特定项目的应用价值
        
        Args:
            paper_id: 论文ID
            project_description: 项目描述
            
        Returns:
            应用建议
        """
        prompt = f"""
        请按照以下步骤操作：
        1. 使用read_paper工具读取ID为"{paper_id}"的论文内容
        2. 分析该论文中的方法、技术或见解如何应用到以下软件工程项目中：
        
        项目描述：{project_description}
        
        请提供：
        - 可以直接应用的具体方法或技术
        - 实施步骤的建议
        - 可能遇到的挑战和解决方案
        - 预期的项目改进效果
        
        回答应该实用、具体，并考虑到软件工程学生的知识水平。
        """
        return await self.chat(prompt)
    
    async def recommend_learning_path(self, topic: str):
        """
        为特定主题推荐学习路径
        
        Args:
            topic: 学习主题
        
        Returns:
            推荐的学习路径和相关论文
        """
        prompt = f"""
        请为软件工程专业学生设计一个关于"{topic}"的学习路径：
        
        1. 首先，使用search_papers工具搜索与"{topic}"相关的软件工程论文，你需要先把{topic}翻译为英文再调用搜索工具
        2. 基于搜索结果，设计一个从入门到进阶的学习路径，包括：
           - 学习这个主题的阶段性目标
           - 推荐阅读顺序（从基础到高级）
           - 每篇论文能学到的关键概念
           - 如何将理论知识与实践项目结合
           - 掌握这一主题的评估标准
        
        请确保学习路径是系统性的，并且考虑到软件工程学生的背景知识。
        """
        return await self.chat(prompt)

async def main():
    paper_agent = PaperAgent()
    await paper_agent.setup()
    result = await paper_agent.search_papers_by_topic("transformer")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
