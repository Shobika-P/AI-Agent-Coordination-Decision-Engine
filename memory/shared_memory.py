class SharedMemory:

    def __init__(self):
        self.memory = {}
        self.history = []

    def save(self, key, value):
        self.memory[key] = value

    def load(self, key):
        return self.memory.get(key)

    def add_history(self, task, decision):
        self.history.append({
            "task": task,
            "decision": decision
        })

    def get_history(self):
        return self.history