"""API使用统计"""

from typing import Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import os

@dataclass
class UsageStats:
    """API使用统计"""
    
    def __init__(self):
        self.session_start = datetime.now()
        self.total_calls = 0
        self.calls_by_role: Dict[str, int] = {}
        self.input_chars_by_role: Dict[str, int] = {}
        self.output_chars_by_role: Dict[str, int] = {}
        self.tokens_by_model: Dict[str, Dict[str, int]] = {}
    
    def add_call(self, role: str, input_chars: int, output_chars: int):
        """记录一次API调用"""
        # 更新总调用次数
        self.total_calls += 1
        
        # 更新角色统计
        if role not in self.calls_by_role:
            self.calls_by_role[role] = 0
            self.input_chars_by_role[role] = 0
            self.output_chars_by_role[role] = 0
            
        self.calls_by_role[role] += 1
        self.input_chars_by_role[role] += input_chars
        self.output_chars_by_role[role] += output_chars
    
    def record_request(self, model: str, role: str, operation: str, tokens_in: int, tokens_out: int):
        """记录一次API请求的使用情况"""
        # 更新模型token统计
        if model not in self.tokens_by_model:
            self.tokens_by_model[model] = {
                "total_tokens_in": 0,
                "total_tokens_out": 0,
                "total_calls": 0,
                "by_role": {}
            }
            
        model_stats = self.tokens_by_model[model]
        model_stats["total_tokens_in"] += tokens_in
        model_stats["total_tokens_out"] += tokens_out
        model_stats["total_calls"] += 1
        
        # 更新角色统计
        if role not in model_stats["by_role"]:
            model_stats["by_role"][role] = {
                "tokens_in": 0,
                "tokens_out": 0,
                "calls": 0,
                "operations": {}
            }
            
        role_stats = model_stats["by_role"][role]
        role_stats["tokens_in"] += tokens_in
        role_stats["tokens_out"] += tokens_out
        role_stats["calls"] += 1
        
        # 更新操作统计
        if operation not in role_stats["operations"]:
            role_stats["operations"][operation] = {
                "tokens_in": 0,
                "tokens_out": 0,
                "calls": 0
            }
            
        op_stats = role_stats["operations"][operation]
        op_stats["tokens_in"] += tokens_in
        op_stats["tokens_out"] += tokens_out
        op_stats["calls"] += 1
        
        # 同时更新字符统计
        self.add_call(role, tokens_in * 4, tokens_out * 4)  # 粗略估算：1 token ≈ 4 字符
    
    def get_summary(self) -> Dict[str, Any]:
        """获取使用统计摘要"""
        total_input_chars = sum(self.input_chars_by_role.values())
        total_output_chars = sum(self.output_chars_by_role.values())
        
        summary = {
            "session_duration": str(datetime.now() - self.session_start),
            "total_calls": self.total_calls,
            "total_chars": {
                "input": total_input_chars,
                "output": total_output_chars,
                "total": total_input_chars + total_output_chars
            },
            "by_role": {
                role: {
                    "calls": self.calls_by_role[role],
                    "input_chars": self.input_chars_by_role[role],
                    "output_chars": self.output_chars_by_role[role],
                    "total_chars": self.input_chars_by_role[role] + self.output_chars_by_role[role]
                }
                for role in self.calls_by_role
            },
            "by_model": self.tokens_by_model
        }
        
        return summary
    
    def save_stats(self, story_id: str = None):
        """保存使用统计到文件"""
        stats_dir = "stats"
        if not os.path.exists(stats_dir):
            os.makedirs(stats_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"usage_stats_{story_id or timestamp}.json"
        filepath = os.path.join(stats_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.get_summary(), f, ensure_ascii=False, indent=2)
            
        return filepath

# 全局单例
_stats = UsageStats()

def get_stats() -> UsageStats:
    """获取全局统计实例"""
    return _stats
