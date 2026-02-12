# 🤖 AI CLI Tool

一个全能的命令行 AI 助手，支持工具调用 (MCP)、YOLO 模式、文件上传、多行交互和多供应商切换。

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

## 📦 零污染环境隔离 (Zero-Pollution)

本工具遵循“不污染系统”原则，所有依赖均在本地运行：
1.  **代码目录**: 默认安装在 `~/ai`。
2.  **私有 Node.js**: 自动下载绿色版 Node.js 到 `~/.config/ai/node`。**不会修改系统 PATH**，不影响系统已有的 Node 环境。
3.  **Python 虚拟环境**: 自动在 `~/.config/ai/python_venv` 创建隔离环境。

### 必须环境
*   **Python 3.8+**: 如果您的系统没有 Python，Linux 脚本会尝试自动安装，Windows 脚本会引导安装。
*   **curl**: 用于下载必要的组件。如果您的系统没有 curl：
    *   **Linux (Debian/Ubuntu)**: `sudo apt install curl`
    *   **Linux (CentOS/Fedora)**: `sudo dnf install curl`
    *   **Windows**: 现代 Windows 10/11 通常自带。如果没有，请在 PowerShell 执行: `winget install curl` 或前往 [curl.se](https://curl.se/windows/) 下载。

---

## 🌟 推荐模型供应商 (兼容 OpenAI 格式)

*   **LongCat (强烈推荐)**: 适配工具调用，免费额度大。URL: `https://api.longcat.chat/openai`
*   **SiliconFlow (硅基流动)**: Llama 3 等模型极速且低成本。URL: `https://api.siliconflow.cn/v1`
*   **DeepSeek**: 代码能力极强，性价比之王。URL: `https://api.deepseek.com`
*   **智谱 AI**: 国产标杆。

---

## 📖 常用命令

*   `ai "帮我写个脚本"`: 快速提问。
*   `ai chat`: 持续对话模式。
*   `ai chat -f ./main.py`: 带上本地文件内容。
*   `ai chat --yolo`: **YOLO 模式**，AI 可以直接操作您的终端。
*   **多行输入**: 对话中输入 `"""` 开启/结束。

---

## 🛠️ 配置与维护
*   `ai new`: 添加新供应商。
*   `ai switch`: 快速切换供应商。
*   `ai model`: 切换模型或创建本地文件夹配置 (`l`)。
*   `ai status`: 查看当前状态。
*   `ai upgrade`: 自动更新工具。
*   `ai uninstall`: 安全卸载。

## 许可证
MIT
