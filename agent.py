import numpy as np

class Agent:
    def __init__(self):
        self.test_count = 0
    
    def get_keep_card(self, state):
        return [0] * 5
    
    def get_keep_dice(self, state):
        e = 'Pyro'
        for i in state['my_state']['characters']:
            if i['active']:
                e = i['element']
                break
        return {i:state['my_state']['current_dice'][i] for i in [e, 'Omni']}
        
    def get_action(self, state):
        try:
            cp = list(range(len(state['action_space'])))
            np.random.shuffle(cp)
            for i in cp:
                # if 'diluc' in i:
                #     return i
                # if 'kaeya' in i:
                #     return i
                j =  state['action_space'][i]
                if j.startswith('event '):
                    return j
                if j.startswith('skill'):
                    return j
            return np.random.choice(state['action_space'])    
        except IndexError:
            return ''
        except ValueError:
            return ''
        
