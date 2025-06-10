from datetime import datetime
from typing import List, Dict, Optional
import json
import os
from pydantic import BaseModel

class ReviewPlanStep(BaseModel):
    """复习计划步骤"""
    id: str
    content: str
    schedule_time: datetime
    is_completed: bool = False
    completion_time: Optional[datetime] = None

class ReviewPlan(BaseModel):
    """复习计划"""
    id: str
    user_id: int
    title: str
    creation_time: datetime
    last_update_time: datetime
    steps: List[ReviewPlanStep]
    progress: float = 0.0
    status: str = "进行中" # 进行中、已完成、已过期

class ReviewPlanManager:
    """复习计划管理器"""
    
    def __init__(self, project_path: str):
        """
        初始化复习计划管理器
        
        Args:
            project_path: 项目路径
        """
        self.plans_dir = os.path.join(project_path, "review_plans")
        os.makedirs(self.plans_dir, exist_ok=True)
    
    def _get_user_plans_path(self, user_id: int) -> str:
        """获取用户复习计划文件路径"""
        return os.path.join(self.plans_dir, f"user_{user_id}_plans.json")
    
    def _load_user_plans(self, user_id: int) -> List[Dict]:
        """加载用户的所有复习计划"""
        file_path = self._get_user_plans_path(user_id)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        else:
            return []
    
    def _save_user_plans(self, user_id: int, plans: List[Dict]) -> None:
        """保存用户的所有复习计划"""
        file_path = self._get_user_plans_path(user_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(plans, f, ensure_ascii=False, indent=2)
    
    def get_user_plans(self, user_id: int, limit: Optional[int] = None) -> List[Dict]:
        """获取用户的复习计划列表"""
        plans = self._load_user_plans(user_id)
        plans.sort(key=lambda x: x.get('last_update_time', ''), reverse=True)
        
        if limit is not None:
            plans = plans[:limit]
            
        return plans
    
    def get_plan_by_id(self, user_id: int, plan_id: str) -> Optional[Dict]:
        """获取特定的复习计划"""
        plans = self._load_user_plans(user_id)
        plan = next((p for p in plans if p.get('id') == plan_id), None)
        return plan
    
    def create_plan(self, user_id: int, plan_data: Dict) -> str:
        """创建新的复习计划"""
        plans = self._load_user_plans(user_id)
        plan_id = f"plan_{user_id}_{int(datetime.now().timestamp())}"
        
        plan = {
            "id": plan_id,
            "user_id": user_id,
            "title": plan_data.get('title', '软件工程复习计划'),
            "creation_time": datetime.now().isoformat(),
            "last_update_time": datetime.now().isoformat(),
            "steps": plan_data.get('steps', []),
            "progress": 0.0,
            "status": "进行中"
        }
        
        plans.append(plan)
        self._save_user_plans(user_id, plans)
        return plan_id
    
    def update_plan(self, user_id: int, plan_id: str, updates: Dict) -> bool:
        """更新复习计划"""
        plans = self._load_user_plans(user_id)
        
        for i, plan in enumerate(plans):
            if plan.get('id') == plan_id:
                # 更新特定字段
                for key, value in updates.items():
                    if key in ['title', 'steps', 'progress', 'status']:
                        plan[key] = value
                
                # 更新最后修改时间
                plan['last_update_time'] = datetime.now().isoformat()
                
                # 如果更新了步骤，重新计算进度
                if 'steps' in updates:
                    completed = sum(1 for step in plan['steps'] if step.get('is_completed', False))
                    total = len(plan['steps'])
                    plan['progress'] = completed / total if total > 0 else 0.0
                
                # 如果所有步骤已完成，更新状态
                if plan['progress'] >= 0.99:
                    plan['status'] = "已完成"
                
                plans[i] = plan
                self._save_user_plans(user_id, plans)
                return True
                
        return False
    
    def update_step_status(self, user_id: int, plan_id: str, step_id: str, is_completed: bool) -> bool:
        """更新复习计划步骤状态"""
        plans = self._load_user_plans(user_id)
        
        for plan_idx, plan in enumerate(plans):
            if plan.get('id') == plan_id:
                steps = plan.get('steps', [])
                
                for step_idx, step in enumerate(steps):
                    if step.get('id') == step_id:
                        # 更新步骤状态
                        step['is_completed'] = is_completed
                        
                        # 如果标记为已完成，添加完成时间
                        if is_completed:
                            step['completion_time'] = datetime.now().isoformat()
                        else:
                            step.pop('completion_time', None)
                        
                        steps[step_idx] = step
                        plan['steps'] = steps
                        
                        # 重新计算进度
                        completed = sum(1 for s in steps if s.get('is_completed', False))
                        total = len(steps)
                        plan['progress'] = completed / total if total > 0 else 0.0
                        
                        # 如果所有步骤已完成，更新状态
                        if plan['progress'] >= 0.99:
                            plan['status'] = "已完成"
                        else:
                            plan['status'] = "进行中"
                        
                        # 更新最后修改时间
                        plan['last_update_time'] = datetime.now().isoformat()
                        
                        plans[plan_idx] = plan
                        self._save_user_plans(user_id, plans)
                        return True
        
        return False
    
    def delete_plan(self, user_id: int, plan_id: str) -> bool:
        """删除复习计划"""
        plans = self._load_user_plans(user_id)
        
        before_count = len(plans)
        plans = [p for p in plans if p.get('id') != plan_id]
        after_count = len(plans)
        
        if before_count == after_count:
            return False
        
        self._save_user_plans(user_id, plans)
        return True
