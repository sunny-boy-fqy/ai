"""
AI CLI 配置管理
配置结构：
~/.config/ai/config/
|-- <供应商>/
|   |-- api      # API密钥列表，每行一个
|   |-- url      # Base URL
|   |-- model    # 模型列表，每行一个
|-- using.config # 当前使用的供应商和模型
"""

import os
import shutil
from typing import List, Optional, Tuple
from .constants import (
    CONFIG_SUBDIR, USING_CONFIG_FILE, BASE_PATH_FILE,
    ensure_dirs, IS_WINDOWS
)
from .ui import UI


class ConfigManager:
    """配置管理器"""
    
    @classmethod
    def init(cls):
        """初始化配置目录"""
        ensure_dirs()
        if not os.path.exists(USING_CONFIG_FILE):
            cls._write_using("", "")
    
    @classmethod
    def get_base_dir(cls) -> str:
        """获取AI安装目录"""
        if os.path.exists(BASE_PATH_FILE):
            try:
                with open(BASE_PATH_FILE, 'r') as f:
                    path = f.read().strip()
                    if path and os.path.isdir(path):
                        return path
            except:
                pass
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    @classmethod
    def set_base_dir(cls, path: str):
        """设置AI安装目录"""
        ensure_dirs()
        with open(BASE_PATH_FILE, 'w') as f:
            f.write(path)
    
    # ========== 供应商管理 ==========
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """列出所有供应商"""
        if not os.path.exists(CONFIG_SUBDIR):
            return []
        return sorted([
            d for d in os.listdir(CONFIG_SUBDIR) 
            if os.path.isdir(os.path.join(CONFIG_SUBDIR, d)) and d != "using.config"
        ])
    
    @classmethod
    def get_provider_dir(cls, name: str) -> str:
        """获取供应商目录"""
        return os.path.join(CONFIG_SUBDIR, name)
    
    @classmethod
    def create_provider(cls, name: str, url: str = "", api: str = "", model: str = ""):
        """创建供应商"""
        ensure_dirs()
        p_dir = cls.get_provider_dir(name)
        os.makedirs(p_dir, exist_ok=True)
        
        if url:
            with open(os.path.join(p_dir, "url"), 'w') as f:
                f.write(url)
        if api:
            with open(os.path.join(p_dir, "api"), 'w') as f:
                f.write(api)
        if model:
            with open(os.path.join(p_dir, "model"), 'w') as f:
                f.write(model)
        
        # 如果没有当前供应商，设为默认
        current = cls.get_current_provider()
        if not current:
            cls.set_current_provider(name)
    
    @classmethod
    def delete_provider(cls, name: str) -> bool:
        """删除供应商"""
        p_dir = cls.get_provider_dir(name)
        if not os.path.exists(p_dir):
            return False
        
        shutil.rmtree(p_dir)
        
        # 如果删除的是当前供应商，清空
        if cls.get_current_provider() == name:
            cls._write_using("", "")
        
        return True
    
    # ========== API管理 ==========
    
    @classmethod
    def get_apis(cls, provider: str) -> List[str]:
        """获取供应商的API列表"""
        api_file = os.path.join(cls.get_provider_dir(provider), "api")
        if not os.path.exists(api_file):
            return []
        try:
            with open(api_file, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except:
            return []
    
    @classmethod
    def add_api(cls, provider: str, api: str):
        """添加API"""
        p_dir = cls.get_provider_dir(provider)
        os.makedirs(p_dir, exist_ok=True)
        api_file = os.path.join(p_dir, "api")
        
        apis = cls.get_apis(provider)
        if api not in apis:
            apis.append(api)
            with open(api_file, 'w') as f:
                f.write('\n'.join(apis))
    
    @classmethod
    def delete_api(cls, provider: str, index: int) -> bool:
        """删除API（用最后一个补位）"""
        apis = cls.get_apis(provider)
        if not (0 <= index < len(apis)):
            return False
        
        # 用最后一个替换
        if len(apis) > 1 and index < len(apis) - 1:
            apis[index] = apis[-1]
        apis = apis[:-1]
        
        api_file = os.path.join(cls.get_provider_dir(provider), "api")
        with open(api_file, 'w') as f:
            f.write('\n'.join(apis))
        return True
    
    @classmethod
    def get_first_api(cls, provider: str) -> Optional[str]:
        """获取第一个可用API"""
        apis = cls.get_apis(provider)
        return apis[0] if apis else None
    
    # ========== URL管理 ==========
    
    @classmethod
    def get_url(cls, provider: str) -> Optional[str]:
        """获取Base URL"""
        url_file = os.path.join(cls.get_provider_dir(provider), "url")
        if not os.path.exists(url_file):
            return None
        try:
            with open(url_file, 'r') as f:
                return f.read().strip()
        except:
            return None
    
    @classmethod
    def set_url(cls, provider: str, url: str):
        """设置Base URL"""
        p_dir = cls.get_provider_dir(provider)
        os.makedirs(p_dir, exist_ok=True)
        with open(os.path.join(p_dir, "url"), 'w') as f:
            f.write(url)
    
    # ========== 模型管理 ==========
    
    @classmethod
    def get_models(cls, provider: str) -> List[str]:
        """获取模型列表"""
        model_file = os.path.join(cls.get_provider_dir(provider), "model")
        if not os.path.exists(model_file):
            return []
        try:
            with open(model_file, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except:
            return []
    
    @classmethod
    def add_model(cls, provider: str, model: str):
        """添加模型"""
        p_dir = cls.get_provider_dir(provider)
        os.makedirs(p_dir, exist_ok=True)
        model_file = os.path.join(p_dir, "model")
        
        models = cls.get_models(provider)
        if model not in models:
            models.append(model)
            with open(model_file, 'w') as f:
                f.write('\n'.join(models))
    
    @classmethod
    def delete_model(cls, provider: str, index: int) -> bool:
        """删除模型（用最后一个补位）"""
        models = cls.get_models(provider)
        if not (0 <= index < len(models)):
            return False
        
        # 用最后一个替换
        if len(models) > 1 and index < len(models) - 1:
            models[index] = models[-1]
        models = models[:-1]
        
        model_file = os.path.join(cls.get_provider_dir(provider), "model")
        with open(model_file, 'w') as f:
            f.write('\n'.join(models))
        return True
    
    # ========== 当前配置 ==========
    
    @classmethod
    def get_current_provider(cls) -> str:
        """获取当前供应商"""
        if not os.path.exists(USING_CONFIG_FILE):
            return ""
        try:
            with open(USING_CONFIG_FILE, 'r') as f:
                lines = f.read().strip().split('\n')
                return lines[0] if lines else ""
        except:
            return ""
    
    @classmethod
    def get_current_model(cls) -> str:
        """获取当前模型"""
        if not os.path.exists(USING_CONFIG_FILE):
            return ""
        try:
            with open(USING_CONFIG_FILE, 'r') as f:
                lines = f.read().strip().split('\n')
                return lines[1] if len(lines) > 1 else ""
        except:
            return ""
    
    @classmethod
    def set_current_provider(cls, provider: str):
        """设置当前供应商"""
        model = cls.get_current_model()
        # 如果切换供应商，尝试获取该供应商的第一个模型
        if provider:
            models = cls.get_models(provider)
            if models and model not in models:
                model = models[0]
        cls._write_using(provider, model)
    
    @classmethod
    def set_current_model(cls, model: str):
        """设置当前模型"""
        provider = cls.get_current_provider()
        cls._write_using(provider, model)
        # 同时添加到模型列表
        if provider and model:
            cls.add_model(provider, model)
    
    @classmethod
    def _write_using(cls, provider: str, model: str):
        """写入当前配置"""
        ensure_dirs()
        with open(USING_CONFIG_FILE, 'w') as f:
            f.write(f"{provider}\n{model}")
    
    # ========== 显示 ==========
    
    @classmethod
    def show_status(cls):
        """显示当前状态"""
        UI.section("当前状态")
        provider = cls.get_current_provider()
        model = cls.get_current_model()
        base_dir = cls.get_base_dir()
        
        UI.item("供应商:", provider or "未设置")
        UI.item("模型:", model or "未设置")
        UI.item("目录:", base_dir)
    
    @classmethod
    def show_list(cls):
        """显示所有配置"""
        UI.section("供应商列表")
        providers = cls.list_providers()
        current = cls.get_current_provider()
        
        if not providers:
            UI.warn("暂无供应商，使用 'ai new <名称>' 创建")
            return
        
        for p in providers:
            marker = "★" if p == current else " "
            url = cls.get_url(p) or "默认"
            apis = cls.get_apis(p)
            models = cls.get_models(p)
            api_count = len(apis)
            model_count = len(models)
            print(f" {marker} {UI.GREEN}{p}{UI.END} - URL: {url} | API: {api_count}个 | 模型: {model_count}个")
    
    # ========== 客户端创建 ==========
    
    @classmethod
    def get_client(cls) -> Tuple[object, str]:
        """获取OpenAI客户端和模型"""
        provider = cls.get_current_provider()
        if not provider:
            return None, ""
        
        api = cls.get_first_api(provider)
        if not api:
            return None, ""
        
        url = cls.get_url(provider)
        model = cls.get_current_model()
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api, base_url=url)
            return client, model
        except:
            return None, ""
