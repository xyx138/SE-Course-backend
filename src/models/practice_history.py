from datetime import datetime
from typing import List, Dict, Optional
import json
import os
from pydantic import BaseModel

class PracticeHistoryItem(BaseModel):
    """习题历史记录项"""
    id: str
    user_id: int
    date: datetime
    topics: List[str]
    count: int
    difficulty: str
    type: str
    questions: List[Dict]

class PracticeHistory:
    """习题历史记录管理器"""
    
    def __init__(self, project_path: str):
        """
        初始化习题历史记录管理器
        
        Args:
            project_path: 项目路径
        """
        self.history_dir = os.path.join(project_path, "practice_history")
        os.makedirs(self.history_dir, exist_ok=True)
    
    def _get_user_history_path(self, user_id: int) -> str:
        """
        获取用户历史记录文件路径
        
        Args:
            user_id: 用户ID
            
        Returns:
            str: 文件路径
        """
        return os.path.join(self.history_dir, f"user_{user_id}.json")
    
    def get_user_history(self, user_id: int, limit: Optional[int] = None) -> List[Dict]:
        """
        获取用户历史记录
        
        Args:
            user_id: 用户ID
            limit: 返回的最大记录数
            
        Returns:
            List[Dict]: 历史记录列表
        """
        file_path = self._get_user_history_path(user_id)
        
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
                
            # 按日期降序排序
            history.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            # 限制返回数量
            if limit is not None:
                history = history[:limit]
                
            return history
        except Exception as e:
            print(f"获取用户历史记录时出错: {e}")
            return []
    
    def add_history_item(self, user_id: int, item: Dict) -> bool:
        """
        添加历史记录项
        
        Args:
            user_id: 用户ID
            item: 历史记录项
            
        Returns:
            bool: 是否成功
        """
        file_path = self._get_user_history_path(user_id)
        
        try:
            # 读取现有历史记录
            history = []
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # 添加新记录
            history.append(item)
            
            # 保存历史记录
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
            return True
        except Exception as e:
            print(f"添加历史记录项时出错: {e}")
            return False
    
    def delete_history_item(self, user_id: int, item_id: str) -> bool:
        """
        删除历史记录项
        
        Args:
            user_id: 用户ID
            item_id: 历史记录项ID
            
        Returns:
            bool: 是否成功
        """
        file_path = self._get_user_history_path(user_id)
        
        if not os.path.exists(file_path):
            return False
        
        try:
            # 读取现有历史记录
            with open(file_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            # 过滤掉要删除的记录
            before_count = len(history)
            history = [item for item in history if item.get('id') != item_id]
            after_count = len(history)
            
            if before_count == after_count:
                return False
            
            # 保存历史记录
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
            return True
        except Exception as e:
            print(f"删除历史记录项时出错: {e}")
            return False
    
    def clear_user_history(self, user_id: int) -> bool:
        """
        清空用户历史记录
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        file_path = self._get_user_history_path(user_id)
        
        if not os.path.exists(file_path):
            return True
        
        try:
            # 清空历史记录
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
                
            return True
        except Exception as e:
            print(f"清空用户历史记录时出错: {e}")
            return False 