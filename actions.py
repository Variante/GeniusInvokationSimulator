from utils import *

class Action:
    def __init__(self, name, pool):
        for i in pool:
            if i['name'] == name:
                data = i
                break
        else:
            print(f'Unknown action card {name}.')
            exit(0)
            
        self.name = name   
        self.cost = data['cost']
        """
        "cost": {
            "d_type": ["Cryo"], elemental dice
            "d_num": [5], required dice
            "p_num": 0, required power
        },
        """
        self.des = data['des']
        self.tags = data['tags']
        self.active_character = data.get('active_character', None)
    """
    def is_affordable(self, dice, character):
        return is_affordable(self.cost, dice, character)
    """
    
    def get_action_space(self, deck):
        res = generate_action_space(self.cost, deck.current_dice, deck.get_current_character(), prefix=f'action {self.name};')
        if count_total_dice(deck.current_dice) > 0:
            for i in deck.current_dice:
                if deck.current_dice[i] > 0:
                    res.append(f'convert {self.name};cost 1 {i};gen 1 {deck.get_current_element()}')
        return res
    
    def state(self):
        return vars(self)
    
    def __repr__(self):
        return json.dumps(self.state())

def init_actions(names):
    # assert len(names) == 30
    pool = load_js('Actions')
    return [Action(name, pool) for name in names]
    
        
