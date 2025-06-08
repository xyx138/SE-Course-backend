import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid
from agents.agent import Agent

class ReviewPlanAgent(Agent):
    """复习计划代理"""
    
    def __init__(self, conversation_logger, practice_history, review_plan_manager):
        """初始化复习计划代理"""
        super().__init__(mcp_servers=[])
        self.conversation_logger = conversation_logger
        self.practice_history = practice_history
        self.review_plan_manager = review_plan_manager
    
    def get_system_prompt(self) -> str:
        system_prompt = """
            你是一个专业的软件工程复习计划制定专家。基于用户的历史对话、练习记录和之前的复习计划，
            生成一个个性化的软件工程课程复习计划。复习计划应该包含以下特点：
            
            1. 针对性：基于用户的历史记录，发现用户的弱点和需要加强的知识点
            2. 结构化：按照清晰的步骤组织，每个步骤包含具体的学习内容和时间安排
            3. 渐进式：从基础到进阶，循序渐进地安排复习内容
            4. 实用性：包含具体的学习资源和练习建议
            5. 可行性：时间安排合理，考虑用户的学习能力和可用时间
            
            
            """
        return system_prompt
    
    async def generate_review_plan(self, user_id: int, username: str) -> Dict[str, Any]:
        """
        生成复习计划
        
        基于用户的历史对话记录、学习笔记和错题集，生成个性化复习计划
        
        Args:
            user_id: 用户ID
            username: 用户名
            
        Returns:
            Dict: 包含复习计划的字典
        """
        try:
            # 1. 获取用户的对话历史
            conversations = self.conversation_logger.get_user_conversations(
                user_id=user_id,
                limit=50  # 获取最近50条记录
            )
            
            # 2. 获取用户的练习历史
            practice_history = self.practice_history.get_user_history(user_id)
            
            # 3. 获取之前的复习计划
            previous_plans = self.review_plan_manager.get_user_plans(user_id)
            

            
            history_data = {
                "conversations": [
                    {
                        "query": conv.get("query", ""),
                        "agent_type": conv.get("agent_type", ""),
                        "timestamp": conv.get("timestamp", 0)
                    } 
                    for conv in conversations
                ],
                "practice_history": [
                    {
                        "topics": item.get("topics", []),
                        "difficulty": item.get("difficulty", ""),
                        "type": item.get("type", ""),
                        "date": item.get("date", "")
                    }
                    for item in practice_history
                ],
                "previous_plans": [
                    {
                        "title": plan.get("title", ""),
                        "creation_time": plan.get("creation_time", ""),
                        "progress": plan.get("progress", 0),
                        "status": plan.get("status", "")
                    }
                    for plan in previous_plans
                ]
            }
            
            user_message = f"""
            用户名：{username}
            用户ID：{user_id}
            
            用户历史数据：
            {json.dumps(history_data, ensure_ascii=False, indent=2)}
            
            请根据用户历史数据，生成一个个性化的软件工程复习计划。输出格式为JSON字符串，不要有任何多余的前后缀：
            {{
                "title": "复习计划标题",
                "summary": "复习计划总体说明",
                "steps": [
                    {{
                        "id": "步骤ID",
                        "content": "步骤内容详细描述",
                        "schedule_time": "计划时间",
                        "is_completed": false
                    }},
                    ...
                ]
            }}
            """
            
            # 调用LLM服务生成计划
            llm_response = await self.chat(user_message)

            # 7. 解析LLM响应
            try:
                if llm_response['status'] == "error":
                    return {
                        "status": "error",
                        "message": llm_response['message']
                    }
                
                plan_data = json.loads(llm_response['message'])
                
                # 为每个步骤生成ID和计划时间（如果没有）
                current_date = datetime.now()
                for i, step in enumerate(plan_data.get("steps", [])):
                    if "id" not in step:
                        step["id"] = f"step_{uuid.uuid4().hex[:8]}"
                    
                    if "schedule_time" not in step:
                        # 默认每天一个步骤
                        step_date = (current_date + timedelta(days=i)).isoformat()
                        step["schedule_time"] = step_date
                    
                    if "is_completed" not in step:
                        step["is_completed"] = False
                
                plan_id = self.review_plan_manager.create_plan(user_id, plan_data)
                
                # 添加计划ID到返回数据
                plan_data["id"] = plan_id
                plan_data["user_id"] = user_id
                plan_data["creation_time"] = datetime.now().isoformat()
                plan_data["last_update_time"] = datetime.now().isoformat()
                plan_data["progress"] = 0.0
                plan_data["status"] = "进行中"
                
                return {
                    "status": "success",
                    "message": "复习计划生成成功",
                    "plan": plan_data
                }
                
            except json.JSONDecodeError as e:
                # JSON解析失败，可能LLM返回的不是有效JSON
                print(f"JSON解析失败: {e}")
                return {
                    "status": "error",
                    "message": f"生成计划格式有误: {str(e)}",
                    "raw_response": llm_response
                }
                
        except Exception as e:
            print(f"生成复习计划时出错: {e}")
            return {
                "status": "error",
                "message": f"生成复习计划时出错: {str(e)}"
            }
