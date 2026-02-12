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

## 📦 依赖说明

### 必须依赖 (Must-have)
1.  **Python 3.8+**: 核心运行环境。
2.  **venv (Python 虚拟环境)**: 脚本会自动创建虚拟环境以隔离依赖，避免污染系统。
3.  **curl**: 用于下载安装包。

### 推荐依赖 (Nice-to-have)
1.  **Git**: 允许脚本通过 `git pull` 自动平滑升级。如果没有 Git，脚本会降级使用 ZIP 下载。
2.  **Node.js & npx**: 如果你需要使用 **MCP 文件系统工具**（允许 AI 读取/写入本地文件），则必须安装 Node.js。

---

## 🌟 推荐模型供应商 (免费/高性价比)

本工具支持所有兼容 OpenAI API 格式的供应商。以下是推荐列表：

### 1. 深度适配 (推荐)
*   **LongCat (推荐)**: 适配度极高，支持工具调用，免费额度大。
    *   URL: `https://api.longcat.chat/openai`
*   **智谱 AI (ZhipuAI)**: 国产大模型标杆，GLM-4 性能强劲，注册送大量 Token。
    *   URL: 驱动选择 `zhipuai` 或使用 OpenAI 兼容格式。

### 2. 高性价比 / 免费渠道
*   **Groq**: 响应速度极快（几百 Token/s），目前有大量免费额度。支持工具调用。
*   **NVIDIA NIM**: 英伟达提供的托管服务，注册后可免费试用主流开源模型（Llama3, Mixtral）。
    *   URL: `https://integrate.api.nvidia.com/v1`
*   **SiliconFlow (硅基流动)**: 国内极速 API 转发，Llama 3 等模型限时免费或极低价格。
    *   URL: `https://api.siliconflow.cn/v1`
*   **DeepSeek**: 性价比极高，代码能力极强。
    *   URL: `https://api.deepseek.com`

### 3. 开源/免费集合项目
*   **GPT_API_FREE**: `https://github.com/chatanywhere/GPT_API_free`
*   **Free-LLM-Collection**: `https://github.com/for-the-zero/Free-LLM-Collection`

---

## 📖 命令行详细用法

### 1. 基础操作
*   `ai "帮我写一个快速排序"`: 快速提问。
*   `ai chat`: 开启持续对话。
*   `ai chat --yolo`: **YOLO 模式**。在此模式下，AI 可以直接调用终端执行命令（如：`ai "帮我把当前目录下的 jpg 改名为 png" --yolo`）。

### 2. 文件与多行交互
*   `ai chat -f ./config.json -f ./main.py`: 同时上传两个文件给 AI 分析。
*   **多行输入**: 在对话中输入 `"""` 开启多行模式，粘贴代码或长文，再次输入 `"""` 结束。

### 3. 配置管理
*   `ai new`: 配置新供应商。
*   `ai switch`: 快速在不同供应商（如 DeepSeek 和 Zhipu）之间切换。
*   `ai model`: 切换模型，或输入 `l` 为当前文件夹生成专属 `.ai-config.json` 配置。
*   `ai delete`: 管理并删除旧的 API Key 或不再使用的供应商。

### 4. 进阶功能 (MCP)
本工具内置了 **Model Context Protocol (MCP)** 支持：
*   **web-search**: AI 可以联网搜索最新的资讯。
*   **filesystem**: AI 可以读取、写入、搜索本地代码库（需在 `ai workspace` 中设置权限路径）。

---

## 🛠️ 系统维护
*   `ai status`: 查看当前生效的设置。
*   `ai upgrade`: 一键更新工具到最新版本。
*   `ai uninstall`: 安全卸载。

## 许可证
MIT
