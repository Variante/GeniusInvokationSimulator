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
        

class RandomAgent(Agent):
    def __init__(self):
        super().__init__()
        
    def get_action(self, state):
        action_space = state.get('action_space', [''])
        if len(action_space) == 0:
            # should not happen, usually..
            action_space = ['']
        return np.random.choice(action_space)
        

class LearnedAgent(Agent):
    def __init__(self, inference):
        super().__init__()
        self.inference = inference
        self.last_state_embedding = None # shape N x 768
        self.last_action_embedding = None # shape 768

    def episode_finished(self):
        info = {
            'state': self.last_state_embedding, # current/last state embedding
            'action': self.last_action_embedding, # current/last action embedding
            'reward': 0,
            'done': True,
        }
        self.last_state_embedding = None
        self.last_action_embedding = None
        return info

    def get_action(self, state):
        action_space = state.get('action_space', [''])
        if len(action_space) == 0:
            # should not happen, usually..
            action_space = ['']
        # it should return the selected action idx and current state embedding
        info = {
            'state': self.last_state_embedding, # current/last state embedding
            'action': self.last_action_embedding, # current/last action embedding
            'reward': 0,
            'done': False,
            'text_state': state['text_state'],
            'text_action_space': state['text_action_space']
        }
        embeddings = self.inference(info)
        action_idx = embeddings['action_idx']
        self.last_state_embedding = embeddings['state']
        self.last_action_embedding = embeddings['action']
        return action_space[action_idx]
