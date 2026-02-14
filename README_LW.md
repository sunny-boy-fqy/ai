# Leader-Worker 模式使用指南

## 概述

Leader-Worker 模式是一个强大的任务执行系统，其中：
- **Leader AI**: 负责任务规划、分配、监控和协调
- **Worker AI**: 负责执行具体任务，使用 MCP 插件自动完成任务

## 快速开始

### 1. 初始化项目

```bash
# 导航到你的项目目录
cd /path/to/your/project

# 初始化 .ai 目录
ai init

# 或者使用自动模式（使用全局配置）
ai init --auto
```

初始化后会创建：
```
.ai/
├── leader_model.config  # Leader 模型配置
├── worker_model.config  # Worker 模型配置
├── workspace.config     # 工作区配置
├── tasks.json          # 任务列表
└── tasks/              # 任务执行目录
```

### 2. 进入工作模式

```bash
ai work
```

### 3. 与 Leader AI 交互

```
Leader> 创建一个简单的 Flask API 项目，包含用户增删改查功能

[Leader] 正在分析需求并规划任务...
已创建 5 个任务

任务进度
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总计: 5 | 完成: 0 | 进行中: 1 | 待处理: 4 | 失败: 0
进度: [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 0.0%

任务列表:
◐ task_001: 创建项目结构 (进行中)
○ task_002: 实现用户模型 (待处理)
○ task_003: 创建数据库连接 (待处理)
○ task_004: 实现 API 路由 (待处理)
○ task_005: 添加测试用例 (待处理)

[Worker 执行] filesystem__create_directory
[Worker 执行] filesystem__write_file
...
```

## 配置说明

### leader_model.config / worker_model.config

```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "api_key": "your-api-key",
  "base_url": "https://api.openai.com/v1/"
}
```

### tasks.json 结构

```json
{
  "project_name": "my-project",
  "created_at": "2024-01-15T10:30:00Z",
  "status": "running",
  "tasks": [
    {
      "id": "task_001",
      "title": "创建项目结构",
      "description": "创建基础目录和文件",
      "type": "code",
      "priority": 1,
      "status": "pending",
      "dependencies": [],
      "files_to_modify": ["app.py", "requirements.txt"],
      "acceptance_criteria": ["目录结构正确", "文件创建成功"]
    }
  ],
  "statistics": {
    "total": 1,
    "pending": 1,
    "in_progress": 0,
    "completed": 0,
    "failed": 0
  }
}
```

## 工作流程

### 1. 用户输入需求
用户使用自然语言描述任务需求。

### 2. Leader AI 规划任务
- 分析需求复杂度
- 拆分为可执行子任务
- 创建 tasks.json
- 设置任务依赖关系

### 3. Leader AI 分配任务
- 检查任务依赖是否满足
- 将 ready 状态的任务分配给 Worker

### 4. Worker AI 执行任务
- 使用 MCP 插件执行具体操作
- 文件操作、代码编写、测试运行等
- 完成后返回结果

### 5. Leader AI 监控进度
- 实时显示任务进度
- 处理 Worker 报告的错误
- 必要时向用户请求帮助

### 6. 完成任务
所有任务完成后生成执行报告。

## 与普通模式的区别

| 特性 | 普通 Chat 模式 | Leader-Worker 模式 |
|------|---------------|-------------------|
| 任务规划 | 一次性响应 | 持续规划调整 |
| 任务执行 | 单次对话 | 多步骤协作 |
| 进度显示 | 无 | 实时进度条 |
| 错误处理 | 需要用户干预 | 自动重试/重新规划 |
| 任务管理 | 无 | 完整的任务系统 |

## 内部接口

### Leader AI 调用 Worker

```python
success, result = await leader.assign_task_to_worker(task)
```

### Worker AI 报告错误给 Leader

```python
# Worker 返回
{
  "status": "failed",
  "error_message": "依赖包安装失败",
  "suggested_solution": "运行 pip install flask"
}

# Leader 处理
if needs_user_help:
    response = leader.request_user_help("需要安装 Flask 框架")
```

### Leader AI 调用其他大模型

```python
# Leader 内部接口
response, tool_calls = await leader.model.call_async(
    prompt="分析这个需求",
    system_prompt="你是需求分析专家",
    tools=available_tools
)
```

## 故障排除

### 初始化失败
```bash
# 检查全局配置
ai status

# 创建供应商
ai new my-provider
```

### Worker 执行失败
1. Leader 会自动尝试重新规划
2. 如果多次失败，会向用户请求帮助
3. 用户可以提供指导或手动处理

### 进度卡住
```bash
# 查看详细状态
> status

# 清空已完成任务
> clear

# 重置所有任务
# (手动编辑 .ai/tasks.json，将所有 status 改为 "pending")
```

## 最佳实践

1. **选择合适的模型**
   - Leader: 使用较强的模型（如 GPT-4o）
   - Worker: 可以使用较快的模型（如 GPT-3.5-turbo）

2. **合理拆分任务**
   - 每个子任务应该在 15-60 分钟内可完成
   - 任务之间尽量减少耦合

3. **及时干预**
   - 当 Leader 请求帮助时及时响应
   - 检查生成的代码是否符合预期

4. **使用 Git**
   - 定期提交代码
   - 任务失败时可以回滚

## 示例场景

### 场景 1: 创建 Web 项目

```
Leader> 创建一个 Express.js 项目，包含用户认证和 REST API

[创建任务中...]
1. 初始化 Node.js 项目
2. 安装必要依赖
3. 创建项目结构
4. 实现用户模型
5. 创建认证中间件
6. 实现 API 路由
7. 添加错误处理
8. 编写测试用例
```

### 场景 2: 重构代码

```
Leader> 重构 utils.js，将重复代码提取为独立函数

[分析现有代码...]
1. 分析 utils.js 结构
2. 识别重复代码模式
3. 设计新的函数接口
4. 实现重构
5. 更新相关调用
6. 运行测试验证
```

### 场景 3: 添加功能

```
Leader> 为用户列表添加分页和搜索功能

[规划任务...]
1. 分析现有 API 结构
2. 设计分页参数
3. 实现搜索逻辑
4. 更新前端调用
5. 添加单元测试
```

## 进阶用法

### 自定义任务

直接编辑 `.ai/tasks.json` 添加任务：

```json
{
  "id": "custom_001",
  "title": "自定义任务",
  "description": "手动添加的任务",
  "type": "code",
  "priority": 2,
  "status": "pending",
  "dependencies": []
}
```

### 查看详细日志

```bash
# 查看任务文件
cat .ai/tasks.json

# 查看任务目录
ls -la .ai/tasks/
```

### 手动触发任务

在工作模式中：
```
Leader> 执行任务 task_002
```
