"""
AI CLI 供应商管理
"""

import os
from typing import List
from .constants import DRIVER_MAP, ensure_dirs
from .config_mgr import ConfigManager
from .ui import UI


class ProviderManager:
    """供应商管理器"""
    
    @classmethod
    def create(cls, name: str = None):
        """创建供应商（交互式）"""
        if not name:
            name = UI.input("供应商名称")
            if not name:
                UI.error("名称不能为空")
                return
        
        # 检查是否已存在
        if name in ConfigManager.list_providers():
            if not UI.confirm(f"'{name}' 已存在，是否覆盖？"):
                return
        
        # 输入配置
        print(f"\n配置供应商: {name}")
        print("驱动类型:")
        for i, (k, v) in enumerate(DRIVER_MAP.items(), 1):
            print(f"  {i}. {v}")
        
        drv_input = UI.input("选择驱动编号", "1")
        try:
            drv_idx = int(drv_input) - 1
            drv_keys = list(DRIVER_MAP.keys())
            if 0 <= drv_idx < len(drv_keys):
                driver = drv_keys[drv_idx]
            else:
                driver = "openai"
        except:
            driver = "openai"
        
        url = UI.input("Base URL", "https://api.openai.com/v1/")
        api = UI.input("API Key")
        model = UI.input("默认模型", "gpt-3.5-turbo")
        
        if not api:
            UI.error("API Key 不能为空")
            return
        
        # 创建
        ConfigManager.create_provider(name, url, api, model)
        UI.success(f"供应商 '{name}' 创建成功")
        
        # 是否切换
        if UI.confirm("切换到此供应商？", default=True):
            ConfigManager.set_current_provider(name)
            UI.success(f"已切换到 '{name}'")
    
    @classmethod
    def use(cls, name: str = None):
        """切换供应商"""
        providers = ConfigManager.list_providers()
        
        if not providers:
            UI.warn("暂无供应商，使用 'ai new <名称>' 创建")
            return
        
        if name:
            if name not in providers:
                UI.error(f"供应商 '{name}' 不存在")
                return
        else:
            current = ConfigManager.get_current_provider()
            print()
            for i, p in enumerate(providers, 1):
                marker = "★" if p == current else " "
                print(f" {marker} {i}. {p}")
            
            inp = UI.input("选择编号")
            if not inp:
                return
            try:
                idx = int(inp) - 1
                if 0 <= idx < len(providers):
                    name = providers[idx]
                else:
                    UI.error("编号无效")
                    return
            except:
                UI.error("请输入编号")
                return
        
        ConfigManager.set_current_provider(name)
        UI.success(f"已切换到 '{name}'")
    
    @classmethod
    def model(cls, name: str = None):
        """切换模型"""
        provider = ConfigManager.get_current_provider()
        if not provider:
            UI.error("未设置供应商，使用 'ai use <名称>' 设置")
            return
        
        models = ConfigManager.get_models(provider)
        current = ConfigManager.get_current_model()
        
        if not name:
            # 显示并选择
            if models:
                UI.section(f"{provider} 的模型")
                for i, m in enumerate(models, 1):
                    marker = "★" if m == current else " "
                    print(f" {marker} {i}. {m}")
                print()
                print("输入编号切换，或输入新模型名添加")
            
            inp = UI.input("模型")
            if not inp:
                return
            
            if inp.isdigit():
                idx = int(inp) - 1
                if 0 <= idx < len(models):
                    name = models[idx]
                else:
                    UI.error("编号无效")
                    return
            else:
                name = inp
                ConfigManager.add_model(provider, name)
        
        ConfigManager.set_current_model(name)
        UI.success(f"模型已切换到 '{name}'")
    
    @classmethod
    def delete(cls, name: str = None):
        """删除供应商"""
        providers = ConfigManager.list_providers()
        
        if not providers:
            UI.warn("暂无供应商")
            return
        
        if not name:
            current = ConfigManager.get_current_provider()
            print()
            for i, p in enumerate(providers, 1):
                marker = "★" if p == current else " "
                print(f" {marker} {i}. {p}")
            
            inp = UI.input("选择要删除的编号")
            if not inp:
                return
            try:
                idx = int(inp) - 1
                if 0 <= idx < len(providers):
                    name = providers[idx]
                else:
                    UI.error("编号无效")
                    return
            except:
                UI.error("请输入编号")
                return
        
        if name not in providers:
            UI.error(f"供应商 '{name}' 不存在")
            return
        
        # 选择删除类型
        print(f"\n供应商: {name}")
        apis = ConfigManager.get_apis(name)
        models = ConfigManager.get_models(name)
        
        print(f"  1. 删除整个供应商")
        print(f"  2. 删除某个API ({len(apis)}个)")
        print(f"  3. 删除某个模型 ({len(models)}个)")
        
        choice = UI.input("选择操作", "1")
        
        if choice == "1":
            if UI.confirm(f"确定删除供应商 '{name}'？"):
                ConfigManager.delete_provider(name)
                UI.success(f"已删除 '{name}'")
        elif choice == "2":
            if not apis:
                UI.warn("无API可删除")
                return
            print()
            for i, api in enumerate(apis, 1):
                print(f"  {i}. {api[:20]}...")
            idx = UI.input("选择API编号")
            if idx.isdigit():
                if ConfigManager.delete_api(name, int(idx) - 1):
                    UI.success("API已删除")
        elif choice == "3":
            if not models:
                UI.warn("无模型可删除")
                return
            print()
            for i, m in enumerate(models, 1):
                marker = "★" if m == ConfigManager.get_current_model() else " "
                print(f" {marker} {i}. {m}")
            idx = UI.input("选择模型编号")
            if idx.isdigit():
                if ConfigManager.delete_model(name, int(idx) - 1):
                    UI.success("模型已删除")
    
    @classmethod
    def show_list(cls):
        """显示供应商列表"""
        ConfigManager.show_list()
    
    @classmethod
    def show_status(cls):
        """显示当前状态"""
        ConfigManager.show_status()
