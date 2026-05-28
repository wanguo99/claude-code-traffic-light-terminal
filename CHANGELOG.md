# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-28

### Added
- 初始版本发布
- 红绿灯状态监控功能
  - 🟢 绿灯：Claude 正在工作
  - 🔴 红灯：需要用户确认
  - 🟡 黄灯：空闲等待输入
- 自动配置 Claude Code hooks
- 配置文件自动备份和还原
- 多项目支持
- 面向对象架构设计
- 完整的类型注解
- 优雅的终端显示界面

### Features
- 无外部依赖，仅使用 Python 标准库
- 自动检测项目名称
- 实时状态更新（0.3 秒轮询间隔）
- 安全的配置管理机制
- 信号处理和优雅退出

[1.0.0]: https://github.com/wanguo99/claude-code-traffic-light-terminal/releases/tag/v1.0.0
