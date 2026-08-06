import json
import os


class SharedMemory:

    def __init__(self):

        self.memory = {}

        self.history_file = "memory/history.json"

        # Create history file if it doesn't exist
        if not os.path.exists(self.history_file):
            with open(self.history_file, "w") as file:
                json.dump([], file)

    # ------------------------
    # Short-Term Memory
    # ------------------------

    def save(self, key, value):
        self.memory[key] = value

    def load(self, key):
        return self.memory.get(key)

    # ------------------------
    # Long-Term Memory
    # ------------------------

    def add_history(self, task, decision):

        history = self.get_history()

        history.append({
            "task": task,
            "decision": decision
        })

        with open(self.history_file, "w") as file:
            json.dump(history, file, indent=4)

    def get_history(self):

        with open(self.history_file, "r") as file:
            return json.load(file)