# CLAUDE.md - GitHub Agent Sim 规则与知识库

## 项目规则
1. 所有数据必须存储在 `D:/GitHub_simulation/data/` 目录，禁止使用 C 盘
2. 每次代码修改前必须先更新 AGENTS.md 和 claude_progress.json
3. 出错处理流程：分析原因 → 给修复方案 → 再改代码 → 记录到 CLAUDE.md
4. 所有公共 API 必须有类型注解
5. 核心模块必须有单元测试，覆盖率 ≥ 80%

## 技术栈
- **语言**: Python 3.11+
- **LLM 框架**: LangChain + LangGraph
- **向量库**: ChromaDB (嵌入式)
- **Git 操作**: GitPython
- **数据存储**: SQLite + JSONL
- **可视化**: Streamlit + Plotly
- **依赖管理**: uv/pip
- **测试**: pytest + pytest-asyncio

## 存储约束
- **总存储**: 5GB 上限
- **分配**: SQLite 3GB + 日志 1GB + 向量 400MB + 原始数据 500MB + 预留 100MB
- **数据目录**: `data/db/`, `data/raw/`, `data/logs/`, `data/vectors/`, `data/cache/`

## 运行命令
- **激活虚拟环境**: `.venv/Scripts/activate` (Windows) 或 `source .venv/bin/activate` (Linux/Mac)
- **运行测试**: `pytest tests/ -v` (必须先激活虚拟环境)
- **运行示例**: `python examples/run_simulation.py` (必须先激活虚拟环境)
- **安装依赖**: `pip install -r pyproject.toml`

## 错误记录
| 日期 | 错误描述 | 原因 | 修复方案 | 状态 |
|------|---------|------|---------|------|
| 2026-03-12 | Windows 文件锁定导致 Git 沙箱清理失败 | Windows 下 Git 对象文件被锁定，shutil.rmtree 无法删除 | 使用 force_cleanup 方法或延迟删除；测试用例需要添加 fixture 清理 | 部分修复 |

## 关键修复记录

### 2026-03-12 - 导入路径修复
- **问题**: 模块导入路径错误
- **原因**: 相对导入层级不正确
- **修复**:
  - `data_pipeline/storage/database.py`: `..config` → `...config`
  - `agents/roles/*.py`: `..agents.base_agent` → `..base_agent`
  - `behavior_extractor.py`: 移除未使用的 `ParseError` 导入
- **文件**: 多个模块文件

## 技术决策
- 存储：SQLite 主数据库 + JSONL 日志
- 智能体框架：LangChain + LangGraph 状态机
- 向量库：ChromaDB 嵌入式
- LLM：通过中间代理访问，API Key 从环境变量读取

## Phase 1 完成模块

### 配置模块
- `config/settings.py` - Pydantic Settings 配置管理

### 数据管道
- `data_pipeline/fetchers/gh_archive.py` - GH Archive 数据获取
- `data_pipeline/processors/event_parser.py` - 事件解析器
- `data_pipeline/processors/behavior_extractor.py` - 行为提取器
- `data_pipeline/storage/database.py` - SQLite 数据库初始化
- `data_pipeline/storage/store.py` - 数据存储接口

### 智能体框架
- `agents/base_agent.py` - 智能体基类
- `agents/perception.py` - 感知模块
- `agents/decision.py` - 决策模块
- `agents/action.py` - 执行模块
- `agents/roles/contributor.py` - Contributor 角色
- `agents/roles/maintainer.py` - Maintainer 角色
- `agents/roles/reviewer.py` - Reviewer 角色
- `agents/roles/bot.py` - Bot 角色
- `agents/prompts/role_templates.py` - 角色 Prompt 模板

### 模拟引擎
- `simulation/git_sandbox.py` - Git 沙箱
- `simulation/event_bus.py` - 事件总线
- `simulation/message_queue.py` - 消息队列和提及系统

### 测试
- `tests/test_config.py` - 配置测试
- `tests/test_git_sandbox.py` - Git 沙箱测试
- `tests/test_event_bus.py` - 事件总线测试
- `tests/test_message_queue.py` - 消息队列测试

### 示例
- `examples/run_simulation.py` - 示例模拟运行脚本

## 最后更新
- **最后更新时间**: 2026-03-13
- **当前 Phase**: Phase 2 - PR 工作流 ✅ 完成

## Phase 2 完成模块

### PR 数据模型
- `database.py` - 新增 `sim_pull_requests`、`sim_pr_reviews` 表
- `store.py` - `PullRequestStore`、`PRReviewStore` 类

### GitSandbox 扩展
- `create_pr()` - 创建 PR
- `merge_pr()` - 合并 PR
- `get_pr()` - 获取 PR 信息
- `add_pr_review()` - 添加 PR 审查

### ActionModule 扩展
- `_handle_create_pr()` - 处理创建 PR
- `_handle_merge_pr()` - 处理合并 PR
- `_handle_review_pr()` - 处理审查 PR
- `merge_pr()` - 便捷方法

### 修复记录
| 问题 | 修复方案 |
|------|---------|
| sandbox 集成问题 | 添加 `sandbox` 属性 setter 同步更新 `git_executor` |
| create_branch 默认参数 | 从 `"main"` 改为 `None` |
| Windows 文件锁定 | cleanup() 添加 retry 和只读处理 |
| PR 唯一约束冲突 | 创建前先检查是否存在 |

## 注意事项
- **虚拟环境**: 所有测试和示例必须在虚拟环境中运行，命令前需执行 `.venv/Scripts/activate`
