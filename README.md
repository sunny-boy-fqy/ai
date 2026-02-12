# 🤖 AI CLI Tool (v1.1)

一个模块化、功能强大的命令行 AI 助手，支持工具调用 (MCP)、对话历史管理、自主插件扩展及多供应商叠加同步。

## 🚀 快速安装

### Linux / macOS
```bash
curl -fsSL https://raw.githubusercontent.com/sunny-boy-fqy/ai/main/install.sh | bash
```

### Windows
```powershell
irm https://raw.githubusercontent.com/sunny-boy-fqy/ai/main/install.ps1 | iex
```

---

## ✨ 核心特性

1.  **模块化设计**: 代码重构为多个工具包（Config, Session, Chat, MCP, Sync），运行更稳定，维护更方便。
2.  **自主插件系统 (Marketplace)**: AI 可以通过 `search_market` 发现数千个 MCP 插件，并自主调用 `install_plugin` 进行安装。
3.  **对话历史 (ai history)**: 对话自动存入 `~/.ai/session`。支持按编号加载旧会话、删除记录或开启新对话。
4.  **智能叠加同步**: `ai download` 和 `ai update` 采用叠加模式，多台设备间的 API Key 自动查重并顺延编号，互不覆盖。
5.  **零污染环境**: 内置私有 Node.js 和 Python 虚拟环境，`ai uninstall` 支持一键彻底清理。

---

## 📖 常用命令

### 对话与交互
*   `ai "帮我写个脚本"`: 快速提问。
*   `ai chat`: 开启持续对话。支持多行输入 (`"""`) 和文件上传 (`-f`)。
*   `ai history`: 查看最近 20 条对话，输入编号继续，输入 `d编号` 删除。

### 配置管理
*   `ai status`: 查看当前活跃的供应商、模型及工作区路径。
*   `ai list`: 列出所有已配置供应商的详细信息。
*   `ai new`: 交互式配置新供应商或追加 API Key。
*   `ai model`: 切换当前供应商的模型或录入新模型。
*   `ai switch`: 快速切换活跃供应商。
*   `ai delete`: 移除特定供应商配置或 API Key（编号自动重排）。

### 系统维护
*   `ai upgrade [v]`: 更新到最新或指定版本。
*   `ai uninstall`: 彻底卸载工具及所有私有环境。

## 许可证
MIT
