#!/usr/bin/env python3
"""
Claude Code 终端红绿灯监控

实时监控 Claude Code 工作状态，通过红绿灯直观显示：
- 🟢 绿灯：Claude 正在工作
- 🔴 红灯：需要用户确认
- 🟡 黄灯：空闲等待输入

Author: wanguo99
License: MIT
"""

import json
import sys
import os
import shutil
import atexit
import signal
import time
import threading
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum


# ==================== 配置 ====================

class Config:
    """全局配置"""
    BASE_DIR = Path.home() / ".claude" / "traffic_light"
    STATE_DIR = BASE_DIR
    CONFIG_PATH = Path.home() / ".claude" / "settings.json"
    BACKUP_PATH = BASE_DIR / "settings_backup.json"
    SELECTED_FILE = BASE_DIR / "selected_project"

    POLL_INTERVAL = 0.3      # 状态轮询间隔（秒）
    BLINK_INTERVAL = 0.5     # 闪烁间隔（秒）

    TRAFFIC_MARKER = "traffic_light_app"  # Hook 标识符
    PERMISSION_TOOLS = "Bash|Write|Edit|NotebookEdit|WebFetch"


# ==================== ANSI 颜色 ====================

class Color:
    """ANSI 颜色代码"""
    RED = '\033[1;31m'
    YELLOW = '\033[1;33m'
    GREEN = '\033[1;32m'
    GRAY = '\033[0;90m'
    CYAN = '\033[1;36m'
    RESET = '\033[0m'


# ==================== 状态定义 ====================

class State(Enum):
    """红绿灯状态"""
    GREEN = "green"   # Claude 正在工作
    RED = "red"       # 需要用户确认
    YELLOW = "yellow" # 空闲等待输入

    @property
    def color(self) -> str:
        """获取状态对应的颜色"""
        return {
            State.GREEN: Color.GREEN,
            State.RED: Color.RED,
            State.YELLOW: Color.YELLOW,
        }[self]

    @property
    def description(self) -> str:
        """获取状态描述"""
        return {
            State.GREEN: "Claude 正在工作",
            State.RED: "需要用户确认",
            State.YELLOW: "空闲等待输入",
        }[self]


@dataclass
class HookConfig:
    """Hook 配置"""
    event: str
    state: State
    matcher: str = ""


# ==================== 项目管理 ====================

class ProjectManager:
    """项目管理器"""

    @staticmethod
    def get_state_file(project_name: Optional[str] = None) -> Path:
        """获取指定项目的状态文件路径"""
        if project_name is None:
            project_name = ProjectManager.get_selected_project()
        return Config.STATE_DIR / f"{project_name}.state"

    @staticmethod
    def get_selected_project() -> str:
        """获取当前选中的项目名"""
        try:
            if Config.SELECTED_FILE.exists():
                return Config.SELECTED_FILE.read_text().strip()
        except Exception:
            pass

        projects = ProjectManager.list_active_projects()
        return projects[0] if projects else "default"

    @staticmethod
    def set_selected_project(project_name: str) -> None:
        """设置当前选中的项目"""
        try:
            Config.SELECTED_FILE.parent.mkdir(parents=True, exist_ok=True)
            Config.SELECTED_FILE.write_text(project_name)
        except Exception:
            pass

    @staticmethod
    def list_active_projects() -> List[str]:
        """列出所有有状态文件的项目"""
        try:
            Config.STATE_DIR.mkdir(parents=True, exist_ok=True)
            return sorted(f.stem for f in Config.STATE_DIR.glob("*.state"))
        except Exception:
            return []


# ==================== 配置管理 ====================

class ConfigManager:
    """配置文件管理器"""

    @staticmethod
    def backup() -> bool:
        """备份原始配置文件"""
        if not Config.CONFIG_PATH.exists():
            return True

        try:
            shutil.copy2(Config.CONFIG_PATH, Config.BACKUP_PATH)
            print(f"✓ 已备份原始配置: {Config.BACKUP_PATH}")
            return True
        except Exception as e:
            print(f"✗ 备份配置失败: {e}")
            return False

    @staticmethod
    def restore() -> None:
        """还原备份的配置文件"""
        if not Config.BACKUP_PATH.exists():
            return

        try:
            shutil.copy2(Config.BACKUP_PATH, Config.CONFIG_PATH)
            Config.BACKUP_PATH.unlink()
            print(f"\n✓ 已还原原始配置: {Config.CONFIG_PATH}")
        except Exception as e:
            print(f"\n✗ 还原配置失败: {e}")

    @staticmethod
    def _is_traffic_hook(entry: dict) -> bool:
        """判断一个 hook 条目是否属于红绿灯"""
        hooks = entry.get("hooks", [])
        return any(Config.TRAFFIC_MARKER in h.get("command", "") for h in hooks)

    @staticmethod
    def _make_hook_entry(command: str, matcher: str = "") -> dict:
        """创建一个符合 Claude Code 格式的 hook 条目"""
        return {
            "matcher": matcher,
            "hooks": [{"type": "command", "command": command}],
        }

    @staticmethod
    def _make_hook_command(state: State) -> str:
        """生成 hook 命令"""
        marker = f"# {Config.TRAFFIC_MARKER}"
        state_dir = Config.STATE_DIR
        return (
            f'project=$(basename "${{CLAUDE_PROJECT_DIR:-$PWD}}") && '
            f'mkdir -p {state_dir} && '
            f'echo {state.value} > {state_dir}/"$project".state {marker}'
        )

    @staticmethod
    def configure_hooks() -> None:
        """配置 Claude Code hooks"""
        Config.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        Config.STATE_DIR.mkdir(parents=True, exist_ok=True)

        ConfigManager.backup()

        # 读取现有配置
        config = {}
        if Config.CONFIG_PATH.exists():
            try:
                config = json.loads(Config.CONFIG_PATH.read_text())
            except Exception:
                config = {}

        hooks = config.get("hooks", {})
        if not isinstance(hooks, dict):
            hooks = {}

        # Hook 配置映射
        hook_configs = [
            HookConfig("SessionStart", State.YELLOW),
            HookConfig("UserPromptSubmit", State.GREEN),
            HookConfig("PermissionRequest", State.RED),
            HookConfig("PreToolUse", State.RED, Config.PERMISSION_TOOLS),
            HookConfig("PostToolUse", State.GREEN, Config.PERMISSION_TOOLS),
            HookConfig("AssistantMessage", State.YELLOW),
            HookConfig("Stop", State.YELLOW),
            HookConfig("SessionEnd", State.YELLOW),
        ]

        # 应用 hook 配置
        for hook_config in hook_configs:
            command = ConfigManager._make_hook_command(hook_config.state)
            new_entry = ConfigManager._make_hook_entry(command, hook_config.matcher)

            existing = hooks.get(hook_config.event, [])
            if not isinstance(existing, list):
                existing = []

            # 清理旧的红绿灯 hooks
            cleaned = [e for e in existing if not ConfigManager._is_traffic_hook(e)]
            cleaned.append(new_entry)

            hooks[hook_config.event] = cleaned
            print(f"✓ 已设置 hook: {hook_config.event}")

        config["hooks"] = hooks

        try:
            Config.CONFIG_PATH.write_text(json.dumps(config, indent=2, sort_keys=True))
            print(f"✓ Claude Code 配置已更新: {Config.CONFIG_PATH}")
        except Exception as e:
            print(f"✗ 写入配置失败: {e}")


# ==================== 红绿灯显示 ====================

class TrafficLight:
    """终端红绿灯显示"""

    LIGHT_HEIGHT = 8  # 每个灯的高度（行数）

    def __init__(self, project_name: Optional[str] = None):
        self.project_name = project_name or ProjectManager.get_selected_project()
        self.state = State.YELLOW
        self.blink_on = True
        self.running = True

    def _draw_light_block(self, is_on: bool, color: str) -> None:
        """绘制一个灯块"""
        if is_on:
            for _ in range(self.LIGHT_HEIGHT):
                print(f"║     {color}████████████████{Color.RESET}     ║")
        else:
            for _ in range(self.LIGHT_HEIGHT):
                print(f"║     {Color.GRAY}▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓{Color.RESET}     ║")

    def draw(self) -> None:
        """绘制红绿灯"""
        # 清屏并移动光标到顶部
        print('\033[2J\033[H', end='')

        # 绘制边框和标题
        print("╔══════════════════════════════╗")
        print("║    Claude Code Status        ║")
        print("╠══════════════════════════════╣")
        print("║                              ║")

        # 红灯
        self._draw_light_block(self.state == State.RED, Color.RED)
        print("║                              ║")

        # 黄灯
        self._draw_light_block(self.state == State.YELLOW, Color.YELLOW)
        print("║                              ║")

        # 绿灯
        self._draw_light_block(self.state == State.GREEN, Color.GREEN)
        print("║                              ║")

        print("╚══════════════════════════════╝")

        # 状态信息
        color = self.state.color
        print(f"\n  {color}█ {self.state.value.upper()}{Color.RESET} - {self.state.description}")
        print(f"\n  {Color.CYAN}项目:{Color.RESET} {self.project_name}")
        print(f"  {Color.CYAN}时间:{Color.RESET} {time.strftime('%H:%M:%S')}")
        print(f"\n  Press Ctrl+C to exit")

    def update_state(self) -> None:
        """从状态文件更新状态"""
        state_file = ProjectManager.get_state_file(self.project_name)

        try:
            if state_file.exists():
                content = state_file.read_text().strip().lower()
                try:
                    new_state = State(content)
                    if self.state != new_state:
                        self.state = new_state
                        self.blink_on = True
                except ValueError:
                    pass
            else:
                if self.state != State.YELLOW:
                    self.state = State.YELLOW
        except Exception:
            pass

    def toggle_blink(self) -> None:
        """切换闪烁状态"""
        self.blink_on = not self.blink_on

    def run(self) -> None:
        """运行主循环"""
        # 闪烁线程
        def blink_worker():
            while self.running:
                time.sleep(Config.BLINK_INTERVAL)
                self.toggle_blink()

        blink_thread = threading.Thread(target=blink_worker, daemon=True)
        blink_thread.start()

        # 主循环
        try:
            while self.running:
                self.update_state()
                self.draw()
                time.sleep(Config.POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\n\n正在退出...")
            self.running = False


# ==================== 主程序 ====================

def setup_signal_handlers() -> None:
    """设置信号处理器"""
    def signal_handler(sig, frame):
        ConfigManager.restore()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main() -> None:
    """主函数"""
    print("=" * 50)
    print("Claude Code 终端红绿灯监控")
    print("=" * 50)
    print()

    # 配置 hooks
    print("正在配置 Claude Code hooks...")
    ConfigManager.configure_hooks()
    print()

    # 注册清理函数
    atexit.register(ConfigManager.restore)
    setup_signal_handlers()

    # 启动监控
    print("启动红绿灯监视器...")
    print()
    time.sleep(1)

    light = TrafficLight()
    light.run()


if __name__ == "__main__":
    main()
