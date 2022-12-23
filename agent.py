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
            cp = [i for i in state['action_space']]
            np.random.shuffle(cp)
            for i in cp:
                # if 'diluc' in i:
                #     return i
                # if 'kaeya' in i:
                #     return i
                if i.startswith('event '):
                    return i
                if i.startswith('skill'):
                    return i
            return np.random.choice(state['action_space'])    
        except IndexError:
            return ''
        except ValueError:
            return ''
        
