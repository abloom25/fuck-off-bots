import json
from pathlib import Path
from typing import List, Set

DATA_FILE = Path("bots.json")

class BotManager:
    def __init__(self):
        self.bot_list: Set[int] = set()
        self.load_data()

    def load_data(self):
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.bot_list = set(data.get("bots", []))
            except Exception as e:
                print(f"Error loading bot list: {e}")
                self.bot_list = set()
        else:
            self.bot_list = set()
            self.save_data()

    def save_data(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({"bots": list(self.bot_list)}, f, indent=4)
        except Exception as e:
            print(f"Error saving bot list: {e}")

    def add_bot(self, qq: int) -> bool:
        if qq not in self.bot_list:
            self.bot_list.add(qq)
            self.save_data()
            return True
        return False

    def remove_bot(self, qq: int) -> bool:
        if qq in self.bot_list:
            self.bot_list.remove(qq)
            self.save_data()
            return True
        return False

    def get_bots(self) -> List[int]:
        return list(self.bot_list)

    def is_bot(self, qq: int) -> bool:
        return qq in self.bot_list

bot_manager = BotManager()
