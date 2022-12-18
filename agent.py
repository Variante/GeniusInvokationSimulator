class Agent:
    def __init__(self):
        self.test_count = 0
    
    def get_keep_dice(self, state):
        return {}
        
    def get_action(self, state):
        self.test_count += 1
        return state['action_space'][0 if self.test_count < 2 else -1]
        
