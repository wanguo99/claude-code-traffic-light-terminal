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
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from contextlib import suppress


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
    RED = '\033[1;91m'      # 亮红色（更显眼）
    YELLOW = '\033[0;33m'   # 暗黄色（降低亮度）
    GREEN = '\033[0;32m'    # 暗绿色（降低亮度）
    GRAY = '\033[2;37m'     # 更浅的灰色（未点亮的灯）
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
        with suppress(Exception):
            if Config.SELECTED_FILE.exists():
                return Config.SELECTED_FILE.read_text().strip()

        projects = ProjectManager.list_active_projects()
        return projects[0] if projects else "default"

    @staticmethod
    def set_selected_project(project_name: str) -> None:
        """设置当前选中的项目"""
        with suppress(Exception):
            Config.SELECTED_FILE.parent.mkdir(parents=True, exist_ok=True)
            Config.SELECTED_FILE.write_text(project_name)

    @staticmethod
    def list_active_projects() -> List[str]:
        """列出所有有状态文件的项目"""
        with suppress(Exception):
            Config.STATE_DIR.mkdir(parents=True, exist_ok=True)
            return sorted(f.stem for f in Config.STATE_DIR.glob("*.state"))
        return []


# ==================== 配置管理 ====================

class ConfigManager:
    """配置文件管理器"""

    @staticmethod
    def _load_config() -> Dict[str, Any]:
        """加载配置文件"""
        if not Config.CONFIG_PATH.exists():
            return {}

        with suppress(Exception):
            return json.loads(Config.CONFIG_PATH.read_text())
        return {}

    @staticmethod
    def _save_config(config: Dict[str, Any]) -> bool:
        """保存配置文件"""
        try:
            Config.CONFIG_PATH.write_text(json.dumps(config, indent=2, sort_keys=True))
            return True
        except Exception as e:
            print(f"✗ 写入配置失败: {e}")
            return False

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
        return (
            f'project=$(basename "${{CLAUDE_PROJECT_DIR:-$PWD}}") && '
            f'mkdir -p {Config.STATE_DIR} && '
            f'echo {state.value} > {Config.STATE_DIR}/"$project".state '
            f'# {Config.TRAFFIC_MARKER}'
        )

    @staticmethod
    def _update_hook(hooks: Dict[str, List], hook_config: HookConfig) -> None:
        """更新单个 hook 配置"""
        command = ConfigManager._make_hook_command(hook_config.state)
        new_entry = ConfigManager._make_hook_entry(command, hook_config.matcher)

        existing = hooks.get(hook_config.event, [])
        if not isinstance(existing, list):
            existing = []

        # 清理旧的红绿灯 hooks 并添加新的
        cleaned = [e for e in existing if not ConfigManager._is_traffic_hook(e)]
        cleaned.append(new_entry)

        hooks[hook_config.event] = cleaned
        print(f"✓ 已设置 hook: {hook_config.event}")

    @staticmethod
    def configure_hooks() -> None:
        """配置 Claude Code hooks"""
        Config.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        Config.STATE_DIR.mkdir(parents=True, exist_ok=True)

        ConfigManager.backup()

        config = ConfigManager._load_config()
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
            HookConfig("Stop", State.YELLOW),
            HookConfig("SessionEnd", State.YELLOW),
        ]

        # 应用所有 hook 配置
        for hook_config in hook_configs:
            ConfigManager._update_hook(hooks, hook_config)

        config["hooks"] = hooks

        if ConfigManager._save_config(config):
            print(f"✓ Claude Code 配置已更新: {Config.CONFIG_PATH}")


# ==================== 红绿灯显示 ====================

class TrafficLight:
    """终端红绿灯显示"""

    LIGHT_HEIGHT = 8  # 每个灯的高度（行数）

    def __init__(self, project_name: Optional[str] = None, enable_beep: bool = False):
        self.project_name = project_name or ProjectManager.get_selected_project()
        self.state = State.YELLOW
        self.blink_on = True
        self.running = True
        self.enable_beep = enable_beep
        self.last_beep_state = None  # 记录上次蜂鸣的状态

    def _draw_light_block(self, is_on: bool, color: str) -> None:
        """绘制一个灯块"""
        block = "████████████████" if is_on else "░░░░░░░░░░░░░░░░"
        display_color = color if is_on else Color.GRAY

        for _ in range(self.LIGHT_HEIGHT):
            print(f"        {display_color}{block}{Color.RESET}        ")

    def draw(self) -> None:
        """绘制红绿灯"""
        os.system('clear' if os.name != 'nt' else 'cls')

        # 标题
        print("╔══════════════════════════════╗")
        print("║    Claude Code Status        ║")
        print("╠══════════════════════════════╣")
        print("║                              ║")

        # 三个灯
        self._draw_light_block(self.state == State.GREEN, Color.GREEN)
        print()
        self._draw_light_block(self.state == State.YELLOW, Color.YELLOW)
        print()
        self._draw_light_block(self.state == State.RED, Color.RED)

        print("║                              ║")
        print("╚══════════════════════════════╝")

        # 状态信息
        color = self.state.color
        print(f" {color}█ {self.state.value.upper()}{Color.RESET} - {self.state.description}")
        print()
        print(f" {Color.CYAN}项目:{Color.RESET} {self.project_name}")
        print(f" {Color.CYAN}时间:{Color.RESET} {time.strftime('%H:%M:%S')}")
        print()
        print(" Press Ctrl+C to exit")
        print("════════════════════════════════", end='', flush=True)

    def update_state(self) -> None:
        """从状态文件更新状态"""
        state_file = ProjectManager.get_state_file(self.project_name)

        with suppress(Exception):
            if not state_file.exists():
                if self.state != State.YELLOW:
                    self.state = State.YELLOW
                return

            content = state_file.read_text().strip().lower()
            with suppress(ValueError):
                new_state = State(content)
                if self.state != new_state:
                    self.state = new_state
                    self.blink_on = True
                    # 根据状态触发不同次数的蜂鸣（仅在启用时）
                    if self.enable_beep:
                        if new_state == State.RED and self.last_beep_state != State.RED:
                            print('\a', end='', flush=True)
                            self.last_beep_state = State.RED
                        elif new_state == State.YELLOW and self.last_beep_state != State.YELLOW:
                            print('\a', end='', flush=True)
                            time.sleep(0.5)
                            print('\a', end='', flush=True)
                            self.last_beep_state = State.YELLOW
                        elif new_state == State.GREEN:
                            self.last_beep_state = None

    def run(self) -> None:
        """运行主循环"""
        def blink_worker():
            while self.running:
                time.sleep(Config.BLINK_INTERVAL)
                self.blink_on = not self.blink_on

        threading.Thread(target=blink_worker, daemon=True).start()

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
    import argparse

    parser = argparse.ArgumentParser(description="Claude Code 终端红绿灯监控")
    parser.add_argument("--beep", action="store_true", help="启用状态切换蜂鸣提示")
    args = parser.parse_args()

    print("=" * 50)
    print("Claude Code 终端红绿灯监控")
    print("=" * 50)
    print()

    print("正在配置 Claude Code hooks...")
    ConfigManager.configure_hooks()
    print()

    atexit.register(ConfigManager.restore)
    setup_signal_handlers()

    beep_status = "已启用" if args.beep else "已禁用"
    print(f"启动红绿灯监视器（蜂鸣提示: {beep_status}）...")
    print()
    time.sleep(1)

    TrafficLight(enable_beep=args.beep).run()


if __name__ == "__main__":
    main()
