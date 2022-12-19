class Agent:
    def __init__(self):
        self.test_count = 0
    
    def get_keep_dice(self, state):
        return {}
        
    def get_action(self, state):
        self.test_count += 1
        try:
            return state['action_space'][0]
        except IndexError:
            return ''
        
