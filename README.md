# AI CLI

智能命令行助手，支持自动发现和安装 MCP 插件。

## 安装

```bash
curl -fsSL https://raw.githubusercontent.com/sunny-boy-fqy/ai/main/install.sh | bash
source ~/.bashrc
```

## 命令

### 对话

| 命令 | 说明 |
|------|------|
| `ai ask <问题>` | 即时问答 |
| `ai chat` | 对话模式 |
| `ai history` | 历史记录 |
| `ai history load <编号>` | 加载历史 |
| `ai history del <编号>` | 删除历史 |

### 供应商

| 命令 | 说明 |
|------|------|
| `ai new <名称>` | 创建供应商 |
| `ai use [名称]` | 切换供应商 |
| `ai model [名称]` | 切换模型 |
| `ai list` | 列出配置 |
| `ai del provider <名称>` | 删除供应商 |

### 插件

| 命令 | 说明 |
|------|------|
| `ai search <关键词>` | 搜索插件 |
| `ai install <名称>` | 安装插件 |
| `ai plugin` | 已装插件 |
| `ai del plugin <名称>` | 卸载插件 |

### 任务

| 命令 | 说明 |
|------|------|
| `ai task add <类型> <命令> [参数]` | 添加任务 |
| `ai task list` | 任务列表 |
| `ai task del <ID>` | 删除任务 |
| `ai task run <ID>` | 立即执行 |
| `ai task start` | 启动守护进程 |
| `ai task stop` | 停止守护进程 |

任务类型: `once`(一次性), `interval`(周期), `schedule`(定时)

### 系统

| 命令 | 说明 |
|------|------|
| `ai sync <仓库>` | 从远程同步配置 |
| `ai update [仓库]` | 更新程序/上传配置 |
| `ai status` | 当前状态 |
| `ai version` | 版本信息 |

### 删除

| 命令 | 说明 |
|------|------|
| `ai del provider <名称>` | 删除供应商 |
| `ai del plugin <名称>` | 卸载插件 |
| `ai del task <ID>` | 删除任务 |
| `ai del history <编号>` | 删除历史 |

## 配置目录

```
~/.config/ai/
├── python_venv/      # Python环境
├── node_venv/        # Node.js环境
├── mcp/              # MCP插件
│   └── mcp.config    # 插件配置
├── config/           # 供应商配置
│   ├── <供应商>/
│   │   ├── api       # API密钥列表
│   │   ├── url       # Base URL
│   │   └── model     # 模型列表
│   └── using.config  # 当前配置
├── history/          # 对话历史
├── tasks.json        # 任务列表
└── base_path.config  # AI目录路径
```

## 内置插件

| 名称 | 功能 | 环境变量 |
|------|------|----------|
| thinking | 思维链推理 | - |
| memory | 知识图谱存储 | - |
| filesystem | 文件操作 | - |
| puppeteer | 浏览器自动化 | - |
| playwright | 浏览器自动化 | - |
| postgres | PostgreSQL | POSTGRES_CONNECTION_STRING |
| sqlite | SQLite数据库 | - |
| github | GitHub API | GITHUB_TOKEN |
| brave-search | 搜索引擎 | BRAVE_API_KEY |
| slack | Slack消息 | SLACK_BOT_TOKEN |

## 示例

### 创建供应商

```bash
ai new openai
# 输入: Base URL、API Key、默认模型
```

### 对话

```bash
# 即时问答
ai ask 帮我写一个Python排序函数

# 对话模式
ai chat
```

### 插件管理

```bash
# 搜索插件
ai search database

# 安装插件
ai install memory

# 查看已安装
ai plugin

# 卸载插件
ai del plugin memory
```

### 任务管理

```bash
# 添加一次性任务
ai task add once "echo hello"

# 添加周期任务(每60秒)
ai task add interval "date" 60

# 查看任务
ai task list

# 执行任务
ai task run 20260213075412
```

### 配置同步

```bash
# 从远程同步
ai sync git@github.com:user/config.git

# 上传配置
ai update git@github.com:user/config.git

# 更新程序
ai update
```

### 历史记录

```bash
# 查看历史
ai history

# 加载历史对话
ai history load 1

# 删除历史
ai history del 1
```

## 自动进化

AI 会自动发现能力差距并安装插件：

```
You > 帮我查询SQLite数据库

AI > ● 调用: analyze_gap
AI > ● 调用: install_plugin
AI > ● 正在安装 sqlite...
AI > ✓ 插件 'sqlite' 安装成功，加载 10 个工具
AI > 现在可以操作数据库了...
```

## 卸载

```bash
rm -rf ~/.config/ai ~/ai
# 从 ~/.bashrc 删除 alias ai=... 行
```

## 依赖

- Python 3.8+
- Node.js 20+ (自动安装到 ~/.config/ai/node_venv/)
- openai, httpx, mcp (自动安装)
