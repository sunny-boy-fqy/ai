# 🤖 AI CLI Tool

一个轻量级、功能强大的命令行 AI 助手，支持多供应商、MCP 工具调用和 YOLO 模式。

## 🚀 快速安装

### Linux / macOS
在终端执行以下命令：
```bash
curl -fsSL https://raw.githubusercontent.com/sunny-boy-fqy/ai/main/install.sh | bash
```

### Windows
在 PowerShell 中执行以下命令：
```powershell
irm https://raw.githubusercontent.com/sunny-boy-fqy/ai/main/install.ps1 | iex
```
该脚本会自动克隆仓库、配置环境并添加 `ai` 命令到 PATH。

## ✨ 主要功能

- **多供应商支持**：OpenAI, ZhipuAI, Groq, DashScope, Anthropic 等。
- **跨平台兼容**：全面支持 Linux 和 Windows 系统。
- **MCP 工具集成**：支持 Model Context Protocol，可扩展搜索、文件操作等工具。
- **YOLO 模式**：允许 AI 直接执行系统 Shell 命令（通过 `--yolo` 开启）。
- **版本管理**：支持自动升级和版本查看。
- **工作区隔离**：可以为不同项目配置独立的工作区和 AI 设置。

## 命令行用法

### 基本查询
```bash
ai "今天天气怎么样？"
ai status        # 显示当前供应商、模型和工作区
ai --version
```

### 交互模式
```bash
ai chat          # 进入普通对话
ai chat --yolo   # 进入 YOLO 模式（慎用！）
```

### 配置管理
```bash
ai new           # 添加 API Key 或新供应商
ai model         # 切换模型或创建本地配置
ai switch        # 快速切换供应商
ai upgrade       # 自动更新至最新版本
```

注意，要求输入的URL是以/v1结尾的那个（openai格式）

### 卸载
```bash
bash ~/ai/uninstall.sh
```

## 🛠️ 配置存储

- **配置文件**: `~/.config/ai/`
- **MCP 服务器**: `~/.ai/mcp_servers/`

## 许可证
MIT
## 免费可用大模型
### 美团的良心longcat(推荐使用，免费方便，可用性强，适配工具)
- longcat.chat
- api接口 URL：https://api.longcat.chat/openai
- 美团是不是应该打一点广告费？

### 可以看这个大佬的仓库
- https://github.com/for-the-zero/Free-LLM-Collection

### github项目 GPT_API_FREE
- https://github.com/chatanywhere/GPT_API_free

### nvidia
- https://build.nvidia.com/




