"""
AI CLI 同步和更新功能
"""

import os
import subprocess
import shutil
from typing import Optional
from .constants import CONFIG_DIR, REPO_URL, ensure_dirs, get_base_dir
from .ui import UI


class SyncManager:
    """同步管理器"""
    
    @classmethod
    def sync_from_remote(cls, repo_url: str = None):
        """从远程仓库同步配置"""
        if not repo_url:
            UI.error("请指定仓库地址")
            UI.info("用法: ai sync git@github.com:user/repo.git")
            return
        
        if not repo_url.startswith("git@"):
            UI.error("仅支持SSH协议 (git@...)")
            return
        
        UI.info("正在从远程同步配置...")
        
        # 创建临时目录
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 克隆仓库
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, tmp_dir],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                UI.error(f"克隆失败: {result.stderr}")
                return
            
            # 合并配置
            src_config = os.path.join(tmp_dir, "config")
            if os.path.exists(src_config):
                dst_config = os.path.join(CONFIG_DIR, "config")
                
                # 合并每个供应商
                for provider in os.listdir(src_config):
                    src_p = os.path.join(src_config, provider)
                    dst_p = os.path.join(dst_config, provider)
                    
                    if os.path.isdir(src_p):
                        os.makedirs(dst_p, exist_ok=True)
                        
                        # 合并API（去重）
                        src_api = os.path.join(src_p, "api")
                        dst_api = os.path.join(dst_p, "api")
                        if os.path.exists(src_api):
                            src_apis = open(src_api).read().strip().split('\n')
                            dst_apis = open(dst_api).read().strip().split('\n') if os.path.exists(dst_api) else []
                            
                            merged = list(set(dst_apis + src_apis))
                            with open(dst_api, 'w') as f:
                                f.write('\n'.join(merged))
                        
                        # 复制URL和模型
                        for f in ["url", "model"]:
                            src_f = os.path.join(src_p, f)
                            dst_f = os.path.join(dst_p, f)
                            if os.path.exists(src_f) and not os.path.exists(dst_f):
                                shutil.copy2(src_f, dst_f)
            
            UI.success("配置同步完成")
    
    @classmethod
    def sync_to_remote(cls, repo_url: str = None):
        """上传配置到远程仓库"""
        if not repo_url:
            UI.error("请指定仓库地址")
            UI.info("用法: ai update git@github.com:user/repo.git")
            return
        
        if not repo_url.startswith("git@"):
            UI.error("仅支持SSH协议 (git@...)")
            return
        
        UI.info("正在上传配置到远程仓库...")
        
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 克隆仓库
            result = subprocess.run(
                ["git", "clone", repo_url, tmp_dir],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                UI.error(f"克隆失败: {result.stderr}")
                return
            
            # 复制配置
            src_config = os.path.join(CONFIG_DIR, "config")
            dst_config = os.path.join(tmp_dir, "config")
            
            if os.path.exists(src_config):
                if os.path.exists(dst_config):
                    shutil.rmtree(dst_config)
                shutil.copytree(src_config, dst_config)
            
            # 提交并推送
            os.chdir(tmp_dir)
            subprocess.run(["git", "add", "."], capture_output=True)
            subprocess.run(["git", "commit", "-m", "AI CLI Config Sync"], capture_output=True)
            result = subprocess.run(["git", "push"], capture_output=True, text=True)
            
            if result.returncode != 0:
                UI.error(f"推送失败: {result.stderr}")
                return
            
            UI.success("配置已上传")


class UpdateManager:
    """更新管理器"""
    
    @classmethod
    def update_self(cls, version: str = None):
        """更新程序"""
        base_dir = get_base_dir()
        
        if not os.path.exists(os.path.join(base_dir, ".git")):
            UI.error("非Git仓库，无法自动更新")
            UI.info("请手动从 https://github.com/sunny-boy-fqy/ai 下载更新")
            return
        
        UI.info("正在检查更新...")
        os.chdir(base_dir)
        
        # 拉取更新
        result = subprocess.run(["git", "pull"], capture_output=True, text=True)
        
        if result.returncode != 0:
            UI.error(f"更新失败: {result.stderr}")
            return
        
        if "Already up to date" in result.stdout or "已是最新" in result.stdout:
            UI.success("已是最新版本")
        else:
            UI.success("更新完成，请重新运行")
    
    @classmethod
    def show_version(cls):
        """显示版本"""
        from .constants import VERSION
        print(f"AI CLI {VERSION}")
