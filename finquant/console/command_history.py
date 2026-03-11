"""
finquant - 命令历史记录

保存和加载命令历史
"""

import json
import os
from pathlib import Path
from typing import List

from finquant.console.config_store import DEFAULT_CONFIG_DIR


class CommandHistory:
    """
    命令历史记录器

    保存用户输入的命令历史
    """

    def __init__(self, config_dir: str = None, max_history: int = 100):
        if config_dir is None:
            self._config_dir = DEFAULT_CONFIG_DIR
        else:
            self._config_dir = Path(config_dir)

        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._history_file = self._config_dir / "command_history.json"
        self._max_history = max_history
        self._history: List[str] = []
        self._load()

    def _load(self):
        """加载历史"""
        if self._history_file.exists():
            try:
                with open(self._history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._history = data.get("commands", [])
            except Exception:
                self._history = []

    def _save(self):
        """保存历史"""
        try:
            with open(self._history_file, "w", encoding="utf-8") as f:
                json.dump({"commands": self._history[-self._max_history:]}, f, ensure_ascii=False)
        except Exception:
            pass

    def add(self, command: str):
        """添加命令"""
        command = command.strip()
        if command and command != self._history[-1] if self._history else True:
            self._history.append(command)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
            self._save()

    def get_history(self, limit: int = 20) -> List[str]:
        """获取历史"""
        return self._history[-limit:]

    def search(self, query: str) -> List[str]:
        """搜索历史"""
        return [cmd for cmd in self._history if query.lower() in cmd.lower()]

    def clear(self):
        """清空历史"""
        self._history = []
        self._save()

    def __len__(self):
        return len(self._history)

    def __getitem__(self, index):
        return self._history[index]


# ========== 便捷函数 ==========

_command_history = None


def get_command_history() -> CommandHistory:
    """获取命令历史"""
    global _command_history
    if _command_history is None:
        _command_history = CommandHistory()
    return _command_history


__all__ = [
    "CommandHistory",
    "get_command_history",
]
