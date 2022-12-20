import numpy as np

class Agent:
    def __init__(self):
        self.test_count = 0
    
    def get_keep_card(self, state):
        return [0] * 5
    
    def get_keep_dice(self, state):
        return {}
        
    def get_action(self, state):
        try:
            for i in state['action_space'][::-1]:
                if i.startswith('action'):
                    return i
            return np.random.choice(state['action_space'])    
        except IndexError:
            return ''
        except ValueError:
            return ''
        
