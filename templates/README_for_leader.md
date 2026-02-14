# Leader AI 任务规划指南

## 角色职责

Leader AI 是任务的总指挥，负责：
1. 分析用户需求，拆解为可执行的小任务
2. 创建任务工作目录和 tasks.json
3. 合理分配任务给 Worker AI
4. 监控整体进度，协调任务依赖关系

## 工作流程

### 1. 接收用户指令

当用户使用 `ai lead "<任务描述>"` 时，Leader AI 开始工作。

### 2. 任务分析

```bash
# Leader AI 首先分析任务复杂度
- 任务涉及哪些领域？（代码、文档、配置等）
- 需要哪些工具/插件？
- 任务之间是否有依赖关系？
- 预估每个子任务的难度和时间
```

### 3. 创建工作目录

```bash
# 在 ~/.ai/ 下创建任务目录
mkdir -p ~/.ai/task_YYYYMMDD_HHMMSS_<task_name>/
```

### 4. 编写 tasks.json

参考 `tasks_example.json` 模板：

```json
{
  "version": "1.0",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "description": "任务总描述",
  "status": "planning",
  "lead_model": "gpt-4",
  "worker_model": "gpt-3.5-turbo",
  "git_enabled": true,
  "tasks": [
    {
      "id": "task_001",
      "title": "任务标题",
      "description": "详细描述要做什么",
      "type": "code|doc|config|test|review",
      "priority": 1,
      "status": "pending",
      "dependencies": [],
      "assigned_to": null,
      "estimated_time": "30m",
      "actual_time": null,
      "files_to_modify": ["file1.py", "file2.js"],
      "acceptance_criteria": ["功能正常", "通过测试"],
      "notes": ""
    }
  ],
  "summary": {
    "total_tasks": 5,
    "completed": 0,
    "failed": 0,
    "progress_percentage": 0
  }
}
```

### 5. 任务状态定义

| 状态 | 说明 |
|------|------|
| `pending` | 等待执行 |
| `ready` | 依赖已满足，可以开始 |
| `assigned` | 已分配给 Worker |
| `in_progress` | Worker 正在执行 |
| `completed` | 已完成并通过验证 |
| `failed` | 执行失败，需要重试或修复 |
| `blocked` | 被阻塞，等待其他任务 |

### 6. 任务类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `code` | 编写代码 | 实现函数、类、模块 |
| `doc` | 编写文档 | README、注释、API文档 |
| `config` | 配置文件 | JSON、YAML、环境变量 |
| `test` | 测试相关 | 单元测试、集成测试 |
| `review` | 代码审查 | 检查、建议、优化 |
| `refactor` | 重构 | 代码优化、结构调整 |
| `fix` | 修复问题 | Bug修复、错误处理 |

### 7. 优先级规则

- **1 (最高)**: 阻塞其他任务的关键路径
- **2 (高)**: 核心功能实现
- **3 (中)**: 一般功能
- **4 (低)**: 优化、增强
- **5 (最低)**: 文档、清理

### 8. 依赖管理

```json
{
  "id": "task_002",
  "dependencies": ["task_001"],
  // task_002 必须等 task_001 完成才能开始
}
```

### 9. Git 策略

如果 `git_enabled: true`：
- 每个任务完成后自动 commit
- Commit message: `[task_id] <task_title>`
- 任务失败时自动回滚到上一个可用版本
- 保留完整的历史记录

### 10. 最佳实践

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

### 11. 错误处理

当任务失败时：
1. 标记任务状态为 `failed`
2. 在 `notes` 中记录失败原因
3. 决定是重试、回滚还是重新规划
4. 更新依赖此任务的其他任务状态为 `blocked`

### 12. 完成报告

所有任务完成后，Leader AI 应该生成：
- 执行摘要
- 修改的文件列表
- 遇到的问题和解决方案
- 后续建议

## 命令参考

```bash
# 启动 Leader 模式（使用默认模型）
ai lead "实现一个用户认证系统"

# 启动 Leader 模式（指定模型）
ai lead --model gpt-4 "实现一个用户认证系统"

# 查看任务状态
ai status

# 手动触发 Worker 执行特定任务
ai work <task_id>

# 暂停任务调度
ai pause

# 恢复任务调度
ai resume

# 终止所有任务
ai abort
```
