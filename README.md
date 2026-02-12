# 🤖 AI CLI Tool

一个轻量级、功能强大的命令行 AI 助手，支持多供应商、MCP 工具调用、文件上传、多行交互和 YOLO 模式。

## 🚀 快速安装
### Linux / macOS
前置需求：curl,python3,python3 venv, git 或 unzip

在终端执行以下命令：
```bash
curl -fsSL https://raw.githubusercontent.com/sunny-boy-fqy/ai/main/install.sh | bash
```

### Windows
前置需求：curl, git (最好有)

在 PowerShell 中执行以下命令：
```powershell
irm https://raw.githubusercontent.com/sunny-boy-fqy/ai/main/install.ps1 | iex
```
该脚本会自动克隆仓库、配置环境并添加 `ai` 命令到 PATH。

## ✨ 主要功能

- **多供应商支持**：OpenAI, 智谱AI, Groq, DashScope, Anthropic 等。
- **跨平台兼容**：全面支持 Linux 和 Windows 系统。
- **工具调用 (MCP)**：支持 Model Context Protocol，可扩展搜索、文件操作等。
- **YOLO 模式**：允许 AI 直接执行系统 Shell 命令（通过 `--yolo` 开启）。
- **文件上传**：支持将本地文件内容发送给 AI 进行分析。
- **多行交互**：支持输入长文本或代码块。
- **工作区管理**：严格限制 AI 对文件系统的访问范围。

## 📖 命令行用法

### 1. 提问与对话
- **快速提问**: `ai "请解释什么是量子力学"`
- **对话模式**: `ai chat`
- **带文件对话**: `ai chat -f ./main.py`
- **YOLO 模式**: `ai chat --yolo` (慎用，AI 可执行系统命令)

### 2. 高级交互
- **上传文件**: 使用 `-f` 或 `--file` 参数。例如：`ai "分析这个日志" -f error.log`
- **多行输入**: 在 `ai chat` 模式下，输入 `"""` 进入多行模式，再次输入 `"""` 结束并发送。

### 3. 配置管理
- **ai new**: 添加 API Key 或配置新的供应商。
- **ai switch**: 在已配置的供应商（如 OpenAI, 智谱）之间快速切换。
- **ai delete**: 删除特定的供应商配置或 API Key。
- **ai model**: 
  - 切换当前供应商使用的模型。
  - 查看模型历史。
  - `l`: 为当前目录生成 `.ai-config.json`，实现项目级配置覆盖。

### 4. 系统维护
- **ai status**: 查看当前使用的供应商、模型、工作区及是否为本地配置。
- **ai workspace [path]**: 设置 AI 的活动目录。默认情况下，AI 只能访问此目录及其子目录（需配合 filesystem MCP）。
- **ai upgrade**: 自动从 GitHub 更新代码并升级虚拟环境。
- **ai uninstall**: 一键卸载 AI 工具及其配置。

## 🛠️ 配置存储

- **配置文件**: `~/.config/ai/`
- **MCP 服务器**: `~/.ai/mcp_servers/`

## 免费可用大模型 (推荐)
- **LongCat**: `https://longcat.chat` (适配工具调用，推荐)
- **GPT_API_FREE**: `https://github.com/chatanywhere/GPT_API_free`

## 许可证
MIT
