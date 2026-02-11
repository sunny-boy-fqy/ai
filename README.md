# 🤖 AI CLI Tool

一个轻量级、功能强大的命令行 AI 助手，支持多供应商、MCP 工具调用和 YOLO 模式。

## 🚀 快速安装

在终端执行以下命令即可一键安装：

```bash
curl -fsSL https://raw.githubusercontent.com/sunny-boy-fqy/ai/main/install.sh | bash
```

## ✨ 主要功能

- **多供应商支持**：OpenAI, ZhipuAI, Groq, DashScope, Anthropic 等。
- **MCP 工具集成**：支持 Model Context Protocol，可扩展搜索、文件操作等工具。
- **YOLO 模式**：允许 AI 直接执行系统 Shell 命令（通过 `--yolo` 开启）。
- **版本管理**：支持自动升级和版本查看。
- **工作区隔离**：可以为不同项目配置独立的工作区和 AI 设置。

## 命令行用法

### 基本查询
```bash
ai "今天天气怎么样？"
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
ai upgrade       # 自动更新至最新版本
```

### 卸载
```bash
bash ~/ai/uninstall.sh
```

## 🛠️ 配置存储

- **配置文件**: `~/.config/ai/`
- **MCP 服务器**: `~/.ai/mcp_servers/`

## 许可证
MIT
