"""
AI CLI 初始化模块
初始化 .ai 目录和配置文件
"""

import os
import json
from typing import Optional, Dict
from ..config_mgr import ConfigManager
from ..ui import UI


class AIInitializer:
    """AI 初始化器"""
    
    def __init__(self, root_dir: str = None):
        """
        初始化器
        
        Args:
            root_dir: 项目根目录，默认为当前目录
        """
        self.root_dir = root_dir or os.getcwd()
        self.ai_dir = os.path.join(self.root_dir, ".ai")
        self.tasks_dir = os.path.join(self.ai_dir, "tasks")
        
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return os.path.isdir(self.ai_dir)
    
    def get_config_files(self) -> Dict[str, str]:
        """获取配置文件路径"""
        return {
            "leader_model": os.path.join(self.ai_dir, "leader_model.config"),
            "worker_model": os.path.join(self.ai_dir, "worker_model.config"),
            "workspace": os.path.join(self.ai_dir, "workspace.config"),
            "tasks": os.path.join(self.ai_dir, "tasks.json"),
        }
    
    def initialize(self, leader_config: Dict = None, worker_config: Dict = None) -> bool:
        """
        初始化 .ai 目录
        
        Args:
            leader_config: leader 模型配置
            worker_config: worker 模型配置
            
        Returns:
            是否成功
        """
        try:
            # 创建目录结构
            os.makedirs(self.ai_dir, exist_ok=True)
            os.makedirs(self.tasks_dir, exist_ok=True)
            
            # 获取配置文件路径
            config_files = self.get_config_files()
            
            # 如果没有提供配置，从全局配置中选择
            if not leader_config:
                leader_config = self._select_model_config("leader")
            if not worker_config:
                worker_config = self._select_model_config("worker")
                
            if not leader_config or not worker_config:
                UI.error("模型配置失败")
                return False
            
            # 写入配置文件
            self._write_model_config(config_files["leader_model"], leader_config)
            self._write_model_config(config_files["worker_model"], worker_config)
            
            # 创建空的 tasks.json
            self._init_tasks_file(config_files["tasks"])
            
            # 创建工作区配置
            workspace_config = os.path.join(self.ai_dir, "workspace.config")
            with open(workspace_config, 'w') as f:
                f.write(self.root_dir)
            
            UI.success(f"初始化完成: {self.ai_dir}")
            return True
            
        except Exception as e:
            UI.error(f"初始化失败: {e}")
            return False
    
    def _select_model_config(self, role: str) -> Optional[Dict]:
        """
        选择模型配置
        
        Args:
            role: "leader" 或 "worker"
            
        Returns:
            模型配置字典
        """
        UI.section(f"选择 {role.upper()} 模型")
        
        # 获取所有供应商
        providers = ConfigManager.list_providers()
        
        if not providers:
            UI.warn("暂无可用供应商")
            print(f"\n  请先创建供应商: ai new <名称>\n")
            return None
        
        # 显示可用供应商
        current = ConfigManager.get_current_provider()
        print()
        for i, p in enumerate(providers, 1):
            marker = "★" if p == current else " "
            models = ConfigManager.get_models(p)
            default_model = models[0] if models else "无模型"
            print(f" {marker} {i}. {p} ({default_model})")
        
        # 选择供应商
        choice = UI.input("选择供应商编号", "1")
        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(providers)):
                UI.error("编号无效")
                return None
            provider = providers[idx]
        except ValueError:
            UI.error("请输入数字")
            return None
        
        # 获取该供应商的模型列表
        models = ConfigManager.get_models(provider)
        
        if models:
            print(f"\n  {provider} 的模型:")
            for i, m in enumerate(models, 1):
                print(f"  {i}. {m}")
            
            model_choice = UI.input("选择模型编号", "1")
            try:
                model_idx = int(model_choice) - 1
                if not (0 <= model_idx < len(models)):
                    model = models[0]
                else:
                    model = models[model_idx]
            except ValueError:
                model = models[0]
        else:
            model = UI.input("输入模型名称", "gpt-3.5-turbo")
        
        # 获取配置信息
        api_key = ConfigManager.get_first_api(provider)
        base_url = ConfigManager.get_url(provider)
        
        return {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "base_url": base_url or "https://api.openai.com/v1/",
        }
    
    def _write_model_config(self, filepath: str, config: Dict):
        """写入模型配置"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def _init_tasks_file(self, filepath: str):
        """初始化任务文件"""
        tasks_data = {
            "project_name": os.path.basename(self.root_dir),
            "created_at": self._get_timestamp(),
            "updated_at": self._get_timestamp(),
            "status": "idle",
            "current_task": None,
            "tasks": [],
            "statistics": {
                "total": 0,
                "pending": 0,
                "in_progress": 0,
                "completed": 0,
                "failed": 0
            }
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(tasks_data, f, ensure_ascii=False, indent=2)
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def load_model_config(self, role: str) -> Optional[Dict]:
        """
        加载模型配置
        
        Args:
            role: "leader" 或 "worker"
            
        Returns:
            配置字典或 None
        """
        config_file = os.path.join(self.ai_dir, f"{role}_model.config")
        
        if not os.path.exists(config_file):
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    def auto_initialize(self) -> bool:
        """
        自动初始化（使用全局配置中的当前供应商和模型）
        
        Returns:
            是否成功
        """
        # 从全局配置获取当前设置
        provider = ConfigManager.get_current_provider()
        model = ConfigManager.get_current_model()
        api_key = ConfigManager.get_first_api(provider) if provider else None
        base_url = ConfigManager.get_url(provider) if provider else None
        
        if not provider or not api_key:
            UI.error("未找到全局配置，请先设置供应商")
            UI.info("使用 'ai new <名称>' 创建供应商")
            return False
        
        config = {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "base_url": base_url or "https://api.openai.com/v1/"
        }
        
        return self.initialize(leader_config=config, worker_config=config)
    
    def show_status(self):
        """显示初始化状态"""
        if not self.is_initialized():
            UI.warn(f"当前目录未初始化: {self.root_dir}")
            UI.info("使用 'ai init' 初始化")
            return
        
        UI.section("AI 配置状态")
        print(f"  目录: {self.ai_dir}")
        print()
        
        # 显示 leader 配置
        leader_config = self.load_model_config("leader")
        if leader_config:
            print(f"  Leader 模型: {leader_config.get('provider')} / {leader_config.get('model')}")
        else:
            print(f"  {UI.YELLOW}Leader 模型: 未配置{UI.END}")
        
        # 显示 worker 配置
        worker_config = self.load_model_config("worker")
        if worker_config:
            print(f"  Worker 模型: {worker_config.get('provider')} / {worker_config.get('model')}")
        else:
            print(f"  {UI.YELLOW}Worker 模型: 未配置{UI.END}")
        
        # 显示任务统计
        tasks_file = self.get_config_files()["tasks"]
        if os.path.exists(tasks_file):
            with open(tasks_file, 'r', encoding='utf-8') as f:
                tasks_data = json.load(f)
            stats = tasks_data.get("statistics", {})
            print()
            print(f"  任务统计:")
            print(f"    总计: {stats.get('total', 0)}")
            print(f"    已完成: {stats.get('completed', 0)}")
            print(f"    进行中: {stats.get('in_progress', 0)}")
            print(f"    待处理: {stats.get('pending', 0)}")
            print(f"    失败: {stats.get('failed', 0)}")
