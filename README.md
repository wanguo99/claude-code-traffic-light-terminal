# Claude Code Traffic Light - Terminal Edition

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/wanguo99/claude-code-traffic-light-terminal)

在终端中通过大号红绿灯直观显示 Claude Code 工作状态的监控工具。

![Demo](docs/demo.gif)

## ✨ 功能特性

- **🖥️ 终端大屏显示**：8 行高的大号方形红绿灯，清晰可见
- **🚦 实时状态指示**：在终端实时显示 Claude Code 工作状态
  - 🟢 **绿灯常亮** — Claude 正在工作
  - 🔴 **红灯常亮** — 需要用户确认（等待权限）
  - 🟡 **黄灯常亮** — 空闲等待输入
  
- **🔔 蜂鸣提示**：可选的状态切换声音提醒（红灯响两次，黄灯响一次）
- **🎯 自动配置**：启动时自动配置 Claude Code hooks，退出时自动还原
- **💾 配置备份**：安全备份原始 `settings.json`，确保不影响现有配置
- **🔄 多项目支持**：自动检测项目名，支持监控多个 Claude Code 会话
- **🎨 优雅设计**：面向对象架构，类型注解，易于维护和扩展
- **⚡ 零依赖**：仅使用 Python 标准库，无需安装额外依赖

## 📦 安装

### 前置要求

- Python 3.7+
- Claude Code CLI

### 快速安装

```bash
# 克隆项目
git clone https://github.com/wanguo99/claude-code-traffic-light-terminal.git
cd claude-code-traffic-light-terminal

# 直接运行（无需额外依赖）
python3 status_light.py
```

## 🚀 使用方法

### 启动监控

```bash
# 基本启动
python3 status_light.py

# 启用蜂鸣提示
python3 status_light.py --beep
```

启动后会：
1. 自动配置 Claude Code hooks
2. 备份原始配置到 `~/.claude/traffic_light/settings_backup.json`
3. 在终端显示大号红绿灯并开始监控

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--beep` | 启用状态切换蜂鸣提示（默认关闭） |

**蜂鸣提示规则**：
- 🔴 红灯：连续响两次（间隔 0.2 秒）
- 🟡 黄灯：响一次
- 🟢 绿灯：不响

### 终端显示效果

```
╔══════════════════════════════╗
║    Claude Code Status        ║
╠══════════════════════════════╣
║                              ║
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║  ← 红灯（灭）
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║
║                              ║
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║  ← 黄灯（灭）
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║
║     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     ║
║                              ║
║     ████████████████     ║  ← 绿灯（亮）
║     ████████████████     ║
║     ████████████████     ║
║     ████████████████     ║
║     ████████████████     ║
║     ████████████████     ║
║     ████████████████     ║
║     ████████████████     ║
║                              ║
╚══════════════════════════════╝

  █ GREEN - Claude 正在工作

  项目: my-project
  时间: 10:30:45

  Press Ctrl+C to exit
```

### 观察状态变化

红绿灯会根据 Claude Code 的工作状态自动变化：

| 状态 | 说明 | 触发时机 |
|------|------|----------|
| 🟢 绿灯 | Claude 正在工作 | 用户发送消息后，Claude 开始思考和执行 |
| 🔴 红灯 | 需要用户确认 | Claude 执行需要权限的操作（读写文件、执行命令等） |
| 🟡 黄灯 | 空闲等待输入 | Claude 回复完成，等待用户下一条消息 |

### 退出

按 `Ctrl+C` 退出，会自动还原原始配置。

## 🔧 工作原理

### Hook 机制

通过 Claude Code 的 hooks 功能，在会话状态变化时写入状态文件：

```
~/.claude/traffic_light/<项目名>.state
```

### Hook 事件映射

| 事件 | 状态 | 说明 |
|------|------|------|
| `SessionStart` | 🟡 黄灯 | 会话开始 |
| `UserPromptSubmit` | 🟢 绿灯 | 用户发送消息 |
| `PreToolUse` | 🔴 红灯 | 执行工具前（需权限） |
| `PostToolUse` | 🟢 绿灯 | 工具执行完成 |
| `AssistantMessage` | 🟡 黄灯 | Claude 回复完成 |
| `Stop/SessionEnd` | 🟡 黄灯 | 会话结束 |

### 状态轮询

脚本定时读取状态文件（0.3 秒间隔），更新终端显示。

## 📁 项目结构

```
claude-code-traffic-light-terminal/
├── status_light.py          # 主程序
├── README.md                # 项目说明
├── LICENSE                  # MIT 许可证
├── CHANGELOG.md             # 更新日志
├── requirements.txt         # 依赖（无外部依赖）
├── .gitignore               # Git 忽略文件
└── docs/
    └── demo.gif             # 演示动图
```

## 🎨 代码架构

```python
Config              # 全局配置
Color               # ANSI 颜色代码
State               # 状态枚举（GREEN/RED/YELLOW）
HookConfig          # Hook 配置数据类
ProjectManager      # 项目管理器
ConfigManager       # 配置文件管理器
TrafficLight        # 红绿灯显示类
```

## 🔒 安全性

- **配置备份**：修改配置前自动备份到 `~/.claude/traffic_light/settings_backup.json`
- **自动还原**：退出时自动还原原始配置
- **非侵入式**：只添加 hooks，不修改其他配置项
- **标识符隔离**：使用 `traffic_light_app` 标识符，避免与其他 hooks 冲突

## 🛠️ 配置说明

应用会自动配置以下路径：

- **状态文件**：`~/.claude/traffic_light/<项目名>.state`
- **配置备份**：`~/.claude/traffic_light/settings_backup.json`
- **项目选择**：`~/.claude/traffic_light/selected_project`

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📮 联系方式

- 提交 Issue: [GitHub Issues](https://github.com/wanguo99/claude-code-traffic-light-terminal/issues)
- 作者: wanguo99
- 邮箱: guohaoprc@163.com
- QQ: 994179396

## 🌟 Star History

如果这个项目对你有帮助，请给个 Star ⭐️

---

**注意**：本项目仅用于监控 Claude Code 状态，不会收集或上传任何数据。
