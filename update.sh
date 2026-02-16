#!/bin/bash

# AI CLI 更新脚本
# 支持多种更新模式：自我更新、推送代码、同步配置

set -e

# ========== 配置 ==========
AI_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REMOTE_URL="git@github.com:sunny-boy-fqy/ai.git"
CONFIG_DIR="$HOME/.config/ai"

# ========== 颜色定义 ==========
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ========== 帮助信息 ==========
show_help() {
    echo -e "${CYAN}AI CLI 更新脚本 v0.2.0${NC}"
    echo ""
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo -e "${YELLOW}命令:${NC}"
    echo "  self        从 GitHub 拉取最新代码（自我更新）"
    echo "  push        推送本地更改到 GitHub"
    echo "  config      同步配置到 Git 仓库"
    echo "  deps        更新 Python/Node 依赖"
    echo "  version     显示当前版本"
    echo "  help        显示此帮助信息"
    echo ""
    echo -e "${YELLOW}push 命令选项:${NC}"
    echo "  -m, --message <msg>   提交信息"
    echo "  -b, --branch <name>   目标分支（默认: dev）"
    echo "  -f, --force           强制推送"
    echo "  -y, --yes             跳过确认"
    echo ""
    echo -e "${YELLOW}config 命令选项:${NC}"
    echo "  <repo_url>    Git 仓库地址（如 git@github.com:user/config.git）"
    echo "  -p, --push    推送配置到远程"
    echo "  -l, --pull    从远程拉取配置"
    echo ""
    echo -e "${YELLOW}示例:${NC}"
    echo "  $0 self                           # 自我更新"
    echo "  $0 push -m '添加新功能' -b main   # 推送到 main 分支"
    echo "  $0 push -y                        # 快速推送（跳过确认）"
    echo "  $0 config -p git@github.com:user/config.git  # 推送配置"
    echo "  $0 config -l git@github.com:user/config.git  # 拉取配置"
    echo "  $0 deps                           # 更新依赖"
}

# ========== 显示版本 ==========
show_version() {
    if [ -f "$AI_DIR/version.txt" ]; then
        VERSION=$(cat "$AI_DIR/version.txt")
        echo -e "${GREEN}AI CLI 版本: ${VERSION}${NC}"
        
        # 检查远程最新版本
        LATEST=$(curl -s "https://raw.githubusercontent.com/sunny-boy-fqy/ai/main/version.txt" 2>/dev/null || echo "")
        if [ -n "$LATEST" ] && [ "$VERSION" != "$LATEST" ]; then
            echo -e "${YELLOW}远程最新版本: ${LATEST}${NC}"
            echo -e "${YELLOW}建议运行 '$0 self' 进行更新${NC}"
        elif [ -n "$LATEST" ]; then
            echo -e "${GREEN}已是最新版本${NC}"
        fi
    else
        echo -e "${RED}版本文件不存在${NC}"
    fi
}

# ========== 自我更新 ==========
self_update() {
    echo -e "${CYAN}=== AI CLI 自我更新 ===${NC}"
    
    cd "$AI_DIR"
    
    # 检查是否有未提交的更改
    if ! git diff --quiet 2>/dev/null || ! git diff --staged --quiet 2>/dev/null; then
        echo -e "${YELLOW}检测到未提交的更改:${NC}"
        git status --short
        echo ""
        read -p "是否暂存这些更改后更新？(y/N): " stash_choice
        if [[ "$stash_choice" =~ ^[Yy]$ ]]; then
            git stash push -m "Auto stash before update $(date +%Y%m%d_%H%M%S)"
            STASHED=true
        else
            echo -e "${RED}更新已取消${NC}"
            exit 1
        fi
    fi
    
    # 确保远程配置正确
    if ! git remote | grep -q origin; then
        git remote add origin "$REMOTE_URL"
    else
        git remote set-url origin "$REMOTE_URL"
    fi
    
    # 获取当前分支
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "main")
    
    echo -e "${BLUE}当前分支: ${CURRENT_BRANCH}${NC}"
    echo -e "${BLUE}正在拉取更新...${NC}"
    
    # 拉取更新
    if git pull origin "$CURRENT_BRANCH" 2>/dev/null; then
        echo -e "${GREEN}✅ 代码更新成功${NC}"
    else
        echo -e "${YELLOW}拉取失败，尝试从 main 分支更新...${NC}"
        git fetch origin main
        git checkout main
        git pull origin main
    fi
    
    # 恢复暂存的更改
    if [ "$STASHED" = true ]; then
        echo -e "${BLUE}恢复暂存的更改...${NC}"
        git stash pop
    fi
    
    # 更新依赖
    echo -e "${BLUE}检查依赖更新...${NC}"
    update_deps
    
    echo -e "${GREEN}✅ 更新完成！${NC}"
    show_version
}

# ========== 推送代码 ==========
push_code() {
    local commit_msg=""
    local target_branch="dev"
    local force_push=false
    local skip_confirm=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -m|--message)
                commit_msg="$2"
                shift 2
                ;;
            -b|--branch)
                target_branch="$2"
                shift 2
                ;;
            -f|--force)
                force_push=true
                shift
                ;;
            -y|--yes)
                skip_confirm=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    echo -e "${CYAN}=== 推送代码到 GitHub ===${NC}"
    
    cd "$AI_DIR"
    
    # 确保远程配置正确
    if ! git remote | grep -q origin; then
        git remote add origin "$REMOTE_URL"
    else
        git remote set-url origin "$REMOTE_URL"
    fi
    
    # 显示当前状态
    echo -e "${BLUE}当前更改:${NC}"
    git status --short
    echo ""
    
    # 获取提交信息
    if [ -z "$commit_msg" ]; then
        if [ "$skip_confirm" = true ]; then
            commit_msg="Update AI CLI $(date +%Y-%m-%d)"
        else
            read -p "输入提交信息: " commit_msg
            if [ -z "$commit_msg" ]; then
                commit_msg="Update AI CLI $(date +%Y-%m-%d)"
            fi
        fi
    fi
    
    # 获取目标分支
    if [ "$skip_confirm" = false ]; then
        read -p "目标分支 [$target_branch]: " input_branch
        if [ -n "$input_branch" ]; then
            target_branch="$input_branch"
        fi
    fi
    
    # 确认推送
    if [ "$skip_confirm" = false ]; then
        echo ""
        echo -e "${YELLOW}即将执行:${NC}"
        echo "  git add ."
        echo "  git commit -m \"$commit_msg\""
        if [ "$force_push" = true ]; then
            echo "  git push -f origin $target_branch"
        else
            echo "  git push origin $target_branch"
        fi
        echo ""
        read -p "确认推送？(y/N): " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            echo -e "${RED}已取消${NC}"
            exit 0
        fi
    fi
    
    # 执行推送
    git add .
    
    # 检查是否有更改需要提交
    if git diff --staged --quiet 2>/dev/null && [ -z "$(git status --porcelain)" ]; then
        echo -e "${YELLOW}没有需要提交的更改${NC}"
    else
        git commit -m "$commit_msg" || true
    fi
    
    # 推送
    echo -e "${BLUE}推送到 $target_branch 分支...${NC}"
    if [ "$force_push" = true ]; then
        git push -f origin "$target_branch"
    else
        git push origin "$target_branch"
    fi
    
    echo -e "${GREEN}✅ 推送完成${NC}"
}

# ========== 同步配置 ==========
sync_config() {
    local repo_url=""
    local mode="push"
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -p|--push)
                mode="push"
                shift
                ;;
            -l|--pull)
                mode="pull"
                shift
                ;;
            git@*|https://*)
                repo_url="$1"
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    if [ -z "$repo_url" ]; then
        echo -e "${RED}错误: 请提供 Git 仓库地址${NC}"
        echo "示例: $0 config -p git@github.com:user/config.git"
        exit 1
    fi
    
    echo -e "${CYAN}=== 配置同步 ===${NC}"
    echo -e "${BLUE}仓库: $repo_url${NC}"
    echo -e "${BLUE}模式: $mode${NC}"
    
    # 创建临时目录
    TEMP_DIR=$(mktemp -d)
    CONFIG_BACKUP="$TEMP_DIR/config_backup"
    
    if [ "$mode" = "push" ]; then
        # 推送配置到远程
        echo -e "${BLUE}备份当前配置...${NC}"
        cp -r "$CONFIG_DIR" "$CONFIG_BACKUP"
        
        echo -e "${BLUE}克隆远程仓库...${NC}"
        git clone "$repo_url" "$TEMP_DIR/repo" 2>/dev/null || {
            echo -e "${RED}克隆失败，请检查仓库地址和权限${NC}"
            rm -rf "$TEMP_DIR"
            exit 1
        }
        
        # 复制配置文件
        echo -e "${BLUE}同步配置文件...${NC}"
        rsync -av --exclude='.git' "$CONFIG_DIR/" "$TEMP_DIR/repo/"
        
        # 提交并推送
        cd "$TEMP_DIR/repo"
        git add .
        git commit -m "Update AI CLI config $(date +%Y-%m-%d)" || true
        git push origin main || git push origin master
        
        echo -e "${GREEN}✅ 配置已推送到远程${NC}"
        
    else
        # 从远程拉取配置
        echo -e "${BLUE}从远程拉取配置...${NC}"
        git clone "$repo_url" "$TEMP_DIR/repo" 2>/dev/null || {
            echo -e "${RED}克隆失败，请检查仓库地址和权限${NC}"
            rm -rf "$TEMP_DIR"
            exit 1
        }
        
        # 备份当前配置
        echo -e "${BLUE}备份当前配置到 $CONFIG_DIR.backup${NC}"
        mv "$CONFIG_DIR" "$CONFIG_DIR.backup" 2>/dev/null || true
        
        # 复制新配置
        cp -r "$TEMP_DIR/repo" "$CONFIG_DIR"
        
        echo -e "${GREEN}✅ 配置已从远程同步${NC}"
    fi
    
    # 清理临时目录
    rm -rf "$TEMP_DIR"
}

# ========== 更新依赖 ==========
update_deps() {
    echo -e "${BLUE}更新 Python 依赖...${NC}"
    
    VENV_PATH="$CONFIG_DIR/python_venv"
    
    if [ -d "$VENV_PATH" ]; then
        "$VENV_PATH/bin/pip" install --upgrade pip -q 2>/dev/null || true
        "$VENV_PATH/bin/pip" install --upgrade openai zhipuai groq httpx mcp pydantic tqdm requests duckduckgo_search -q 2>/dev/null || true
        echo -e "${GREEN}✅ Python 依赖已更新${NC}"
    else
        echo -e "${YELLOW}Python 虚拟环境不存在，跳过${NC}"
    fi
}

# ========== 主函数 ==========
main() {
    local command="${1:-help}"
    
    case $command in
        self)
            self_update
            ;;
        push)
            shift
            push_code "$@"
            ;;
        config)
            shift
            sync_config "$@"
            ;;
        deps)
            update_deps
            ;;
        version|-v|--version)
            show_version
            ;;
        help|-h|--help)
            show_help
            ;;
        *)
            echo -e "${RED}未知命令: $command${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
