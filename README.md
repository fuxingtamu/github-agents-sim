# GitHub Agent Sim

GitHub 开发者行为多智能体模拟系统

## 项目简介

本项目旨在构建一个**能力对齐真实开发者的多智能体系统**，用于模拟 GitHub 开发者行为和协作模式。

### 核心目标

1. **个人能力对齐** - 智能体具备真实 GitHub 参与者的完整能力栈（读写代码、运行测试、发起讨论、审查代码等）
2. **交互能力对齐** - 智能体之间能像真实开发者一样自由交流、协作、争论、决策
3. **行为模式对齐** - 基于真实数据训练，行为风格符合角色定位

### 设计原则

> **真实有什么能力，智能体也要有什么能力**

## 快速开始

### 环境要求

- Python 3.11+
- Git

### 安装

```bash
# 克隆仓库
git clone <repo-url>
cd github-agent-sim

# 安装依赖（使用 uv 或 pip）
uv pip install -e ".[dev,analysis]"

# 或者使用 pip
pip install -e ".[dev,analysis]"
```

### 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 配置 LLM API 和其他设置
```

### 运行示例

```bash
# 运行示例模拟
python examples/run_simulation.py

# 运行测试
pytest tests/ -v

# 运行测试并生成覆盖率报告
pytest tests/ -v --cov=src/github_agent_sim --cov-report=html
```

## 项目结构

```
github-agent-sim/
├── src/github_agent_sim/       # 主要源代码
│   ├── agents/                 # 智能体模块
│   │   ├── base_agent.py       # 智能体基类
│   │   ├── perception.py       # 感知模块
│   │   ├── decision.py         # 决策模块
│   │   ├── action.py           # 执行模块
│   │   └── roles/              # 角色实现
│   │       ├── maintainer.py   # 维护者
│   │       ├── contributor.py  # 贡献者
│   │       ├── reviewer.py     # 审查者
│   │       └── bot.py          # 机器人
│   ├── simulation/             # 模拟引擎
│   │   ├── git_sandbox.py      # Git 沙箱
│   │   ├── event_bus.py        # 事件总线
│   │   └── message_queue.py    # 消息队列
│   ├── data_pipeline/          # 数据管道
│   │   ├── fetchers/           # 数据获取
│   │   ├── processors/         # 数据处理
│   │   └── storage/            # 数据存储
│   └── config/                 # 配置管理
├── tests/                      # 测试文件
├── examples/                   # 示例脚本
├── config/                     # 配置文件
└── data/                       # 数据目录
```

## 智能体角色

### Maintainer (维护者)
- 审批 PR、合并代码
- 管理 Issue 和 Label
- 分配任务

### Contributor (贡献者)
- 创建分支、提交代码
- 发起 PR
- 响应审查意见

### Reviewer (审查者)
- 审查 PR 代码质量
- 提出建设性意见
- 批准或请求变更

### Bot (自动化机器人)
- 运行 CI/CD 测试
- 自动添加 Label
- 报告构建状态

## 性格类型

| 类型 | 特点 | 审查风格 |
|------|------|---------|
| 守门员型 | 严格、详细、慢响应 | 5-10 条评论，正式语气 |
| 导师型 | 友好、建设性、爱帮忙 | 2-5 条建议，鼓励性 |
| 忍者型 | 高效、沉默、独立 | LGTM 或直接指出问题 |
| 协作型 | 爱交流、@他人、促共识 | 组织讨论，促进共识 |
| 猎虫型 | 找 bug、详细报告 | 详细复现步骤 |
| 架构师型 | 系统思考、长期规划 | 长文分析架构问题 |

## 存储管理

项目使用 5GB 存储限制：

| 用途 | 分配 | 说明 |
|------|------|------|
| SQLite 数据库 | 3GB | 开发者画像、行为记录 |
| 模拟日志 | 1GB | 保留最近 10 次模拟 |
| 向量索引 | 400MB | RAG 检索 |
| 原始数据 | 500MB | 采样数据 |

## 开发指南

### 运行测试

```bash
pytest tests/ -v
```

### 代码质量

```bash
# 格式化
black src/ tests/

# 类型检查
mypy src/

# Lint
ruff check src/ tests/
```

## 技术栈

- **语言**: Python 3.11+
- **LLM 框架**: LangChain + LangGraph
- **向量库**: ChromaDB
- **Git 操作**: GitPython
- **数据存储**: SQLite + JSONL
- **可视化**: Streamlit + Plotly

## 许可证

MIT License

## 贡献

欢迎贡献！请阅读贡献指南了解如何参与。
