import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

class ConversationLogger:
    """
    用户与Agent对话记录记录器
    
    负责将用户和各种Agent的对话记录保存到JSON文件中
    每个用户有一个独立的JSON文件存储其所有对话
    """
    
    def __init__(self, logs_dir: str):
        """
        初始化对话记录器
        
        Args:
            logs_dir: 日志文件存储目录
        """
        self.logs_dir = logs_dir
        # 确保日志目录存在
        self.conversations_dir = os.path.join(logs_dir, "conversations")
        os.makedirs(self.conversations_dir, exist_ok=True)
    
    def _get_user_log_file(self, user_id: int) -> str:
        """
        获取用户的日志文件路径
        
        Args:
            user_id: 用户ID
            
        Returns:
            str: 用户日志文件的完整路径
        """
        return os.path.join(self.conversations_dir, f"user_{user_id}_conversations.json")
    
    def _load_user_conversations(self, user_id: int) -> Dict:
        """
        加载用户的所有对话记录
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 用户的所有对话记录
        """
        log_file = self._get_user_log_file(user_id)
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                # 文件存在但不是有效的JSON，返回空记录
                return {"user_id": user_id, "conversations": []}
        else:
            # 文件不存在，返回空记录
            return {"user_id": user_id, "conversations": []}
    
    def _save_user_conversations(self, user_id: int, conversations: Dict) -> None:
        """
        保存用户的所有对话记录
        
        Args:
            user_id: 用户ID
            conversations: 要保存的对话记录
        """
        log_file = self._get_user_log_file(user_id)
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, ensure_ascii=False, indent=2)
    
    def log_conversation(self, 
                         user_id: int, 
                         username: str,
                         agent_type: str, 
                         query: str, 
                         response: Dict[str, Any]) -> None:
        """
        记录一次对话
        
        Args:
            user_id: 用户ID
            username: 用户名
            agent_type: Agent类型
            query: 用户查询
            response: Agent响应
        """
        # 加载现有对话
        conversations = self._load_user_conversations(user_id)
        
        # 创建新的对话记录
        timestamp = int(time.time())
        formatted_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        conversation = {
            "id": f"{user_id}_{timestamp}",
            "timestamp": timestamp,
            "datetime": formatted_time,
            "agent_type": agent_type,
            "query": query,
            "response": response,
        }
        
        # 添加到对话列表
        conversations["conversations"].append(conversation)
        
        # 保存更新后的对话记录
        self._save_user_conversations(user_id, conversations)
    
    def get_user_conversations(self, 
                               user_id: int, 
                               limit: Optional[int] = None, 
                               agent_type: Optional[str] = None) -> List[Dict]:
        """
        获取用户的对话记录
        
        Args:
            user_id: 用户ID
            limit: 返回的最大记录数，None表示返回所有记录
            agent_type: 可选的Agent类型过滤条件
            
        Returns:
            List[Dict]: 用户的对话记录列表
        """
        conversations = self._load_user_conversations(user_id)
        result = conversations["conversations"]
        
        # 按Agent类型过滤
        if agent_type:
            result = [conv for conv in result if conv["agent_type"] == agent_type]
        
        # 按时间戳倒序排序（最新的在前）
        result.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # 限制返回数量
        if limit and len(result) > limit:
            result = result[:limit]
            
        return result 