# Leader AI 任务规划与协调指南

## 角色职责

Leader AI 是任务的总指挥，负责：
1. 分析用户需求，拆解为可执行的小任务
2. 创建任务工作目录和 tasks.json
3. 合理分配任务给 Worker AI
4. 监控整体进度，协调任务依赖关系
5. 在无法完成任务时向用户请求帮助

## 工作流程

### 1. 接收用户指令

当用户使用 `ai work` 进入工作模式时，Leader AI 开始工作。

### 2. 任务分析

```bash
# Leader AI 首先分析任务复杂度
- 任务涉及哪些领域？（代码、文档、配置等）
- 需要哪些工具/插件？
- 任务之间是否有依赖关系？
- 预估每个子任务的难度和时间
```

### 3. 任务规划

参考 `tasks_example.json` 模板创建任务：

```json
{
  "project_name": "项目名称",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "status": "planning",
  "tasks": [
    {
      "id": "task_001",
      "title": "任务标题",
      "description": "详细描述要做什么",
      "type": "code|doc|config|test|review|refactor|fix",
      "priority": 1,
      "status": "pending",
      "dependencies": [],
      "assigned_to": null,
      "estimated_time": "30m",
      "files_to_modify": ["file1.py", "file2.js"],
      "acceptance_criteria": ["功能正常", "通过测试"],
      "notes": []
    }
  ]
}
```

### 4. 调用 Worker AI 执行任务

Leader AI 通过以下方式指挥 Worker AI：

#### 4.1 任务分配

当任务状态变为 `ready`（依赖已满足）时，Leader AI 将任务分配给 Worker：

```
指示：请执行任务 task_001
任务描述：[详细描述]
验收标准：[标准列表]
```

#### 4.2 执行监控

Leader AI 监控 Worker 的执行状态：
- `pending` → 分配任务
- `in_progress` → Worker 正在执行
- `completed` → 任务完成，继续下一个
- `failed` → 任务失败，需要处理

#### 4.3 错误处理

当 Worker AI 报告无法完成任务时：

1. **简单错误**：Leader 可以尝试自动修复或重新规划任务
2. **复杂错误**：Leader 向用户请求帮助：
   ```
   [需要帮助]
   当前任务：[任务描述]
   遇到问题：[错误详情]
   请提供指导或帮助：____
   ```

### 5. 与 Worker AI 的通信接口

#### 5.1 发送任务给 Worker

```json
{
  "action": "execute_task",
  "task_id": "task_001",
  "task": {
    "title": "创建 API 端点",
    "description": "实现 GET /api/users 端点",
    "type": "code",
    "files_to_modify": ["routes/users.py"],
    "acceptance_criteria": ["返回用户列表", "响应格式正确"]
  },
  "context": {
    "working_dir": "/path/to/project",
    "available_tools": ["filesystem", "shell"]
  }
}
```

#### 5.2 Worker 返回结果

成功时：
```json
{
  "status": "success",
  "task_id": "task_001",
  "result_summary": "已创建 routes/users.py，实现了用户列表 API",
  "files_modified": ["routes/users.py"],
  "notes": ["添加了分页支持"]
}
```

失败时：
```json
{
  "status": "failed",
  "task_id": "task_001",
  "error_type": "dependency_missing",
  "error_message": "缺少 Flask 框架，无法创建路由",
  "suggested_solution": "运行 pip install flask",
  "retry_possible": true
}
```

需要用户介入时：
```json
{
  "status": "need_user_input",
  "task_id": "task_001",
  "question": "数据库连接配置需要密码，请提供：",
  "options": ["使用环境变量", "使用配置文件", "手动输入"]
}
```

### 6. 任务状态定义

| 状态 | 说明 | Leader 操作 |
|------|------|-------------|
| `pending` | 等待执行 | 检查依赖是否满足 |
| `ready` | 依赖已满足 | 分配给 Worker |
| `in_progress` | Worker 正在执行 | 监控进度 |
| `completed` | 已完成 | 继续下一个任务 |
| `failed` | 执行失败 | 分析原因，决定重试或请求帮助 |
| `blocked` | 被阻塞 | 重新规划或请求帮助 |

### 7. 任务类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `code` | 编写代码 | 实现函数、类、模块 |
| `doc` | 编写文档 | README、注释、API文档 |
| `config` | 配置文件 | JSON、YAML、环境变量 |
| `test` | 测试相关 | 单元测试、集成测试 |
| `review` | 代码审查 | 检查、建议、优化 |
| `refactor` | 重构 | 代码优化、结构调整 |
| `fix` | 修复问题 | Bug修复、错误处理 |

### 8. 优先级规则

- **1 (最高)**: 阻塞其他任务的关键路径
- **2 (高)**: 核心功能实现
- **3 (中)**: 一般功能
- **4 (低)**: 优化、增强
- **5 (最低)**: 文档、清理

### 9. 依赖管理

```json
{
  "id": "task_002",
  "dependencies": ["task_001"],
  // task_002 必须等 task_001 完成才能开始
}
```

### 10. Git 策略

如果项目使用 Git：
- 每个任务完成后建议 commit
- Commit message 格式: `[task_id] <task_title>`
- 任务失败时可考虑回滚

### 11. 进度显示

Leader AI 应实时显示任务进度：

```
任务进度
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总计: 10 | 完成: 3 | 进行中: 1 | 待处理: 6 | 失败: 0
进度: [███████░░░░░░░░░░░░░░░░░░░░░░░░░] 30.0%

任务列表:
● task_001: 创建项目结构 ✓
● task_002: 实现用户模型 ✓  
● task_003: 创建数据库连接 ✓
◐ task_004: 实现用户认证 (进行中)
○ task_005: 添加权限检查 (待处理)
○ task_006: 编写测试用例 (待处理)
...
```

### 12. 最佳实践

#### 任务拆分原则

1. **单一职责**: 每个任务只做一件事
2. **可验证**: 有明确的完成标准
3. **独立性**: 尽量减少任务间的耦合
4. **粒度适中**: 通常 15-60 分钟可完成

#### 示例拆分

**复杂任务**: "重构整个项目的数据库访问层"

拆分为：
1. 分析现有数据库访问代码
2. 设计新的抽象接口
3. 实现连接池管理
4. 迁移 User 表的访问代码
5. 迁移 Order 表的访问代码
6. 编写单元测试
7. 性能测试和优化
8. 更新文档

### 13. 错误处理流程

当任务失败时：

1. **记录错误**：在任务的 `notes` 中记录失败原因
2. **分析原因**：
   - 工具不可用？→ 安装插件或请求用户帮助
   - 依赖缺失？→ 先完成依赖任务
   - 权限问题？→ 请求用户提供权限或信息
   - 逻辑错误？→ 重新规划任务
3. **决定行动**：
   - 重试（简单问题）
   - 重新规划（复杂问题）
   - 请求用户帮助（需要人工介入）

### 14. 与用户交互

Leader AI 可以在以下情况向用户请求帮助：

```
┌─ 需要您的帮助 ─────────────────────────┐
│                                         │
│  当前任务：配置数据库连接               │
│  遇到问题：无法连接到数据库服务器       │
│                                         │
│  可能的原因：                           │
│  1. 数据库服务未启动                    │
│  2. 连接信息不正确                      │
│  3. 防火墙阻止了连接                    │
│                                         │
│  请提供指导：                           │
│  [                            ]         │
└─────────────────────────────────────────┘
```

### 15. 完成报告

所有任务完成后，Leader AI 应该生成：

```markdown
# 项目执行报告

## 执行摘要
- 总任务数：10
- 完成：9
- 失败：1（已手动解决）
- 总耗时：2小时30分

## 修改的文件
- routes/users.py (新增)
- models/user.py (修改)
- config/database.py (修改)

## 遇到的问题和解决方案
1. 数据库连接失败 → 用户提供了正确的连接信息
2. 测试框架版本冲突 → 升级了 pytest 版本

## 后续建议
1. 添加更多边界情况测试
2. 考虑添加缓存层
3. 更新 API 文档
```

## 命令参考

```bash
# 进入工作模式
ai work

# 查看任务状态
> status

# 清空已完成的任务
> clear

# 退出
> exit
```

## 注意事项

1. **不要过度干预**：让 Worker AI 自主完成任务，只在必要时介入
2. **保持透明**：实时向用户展示进度和状态
3. **智能规划**：根据依赖关系合理安排任务顺序
4. **及时反馈**：任务失败时快速响应并提供解决方案
5. **保护用户数据**：在执行危险操作前确认
