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
        self.code_name = data['code_name']
        self.code = data['code']
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
        
        if 'food' in self.tags:
            self.code += ';feed'
        
        
        self.active_character = data.get('active_character', None)
    """
    def is_affordable(self, dice, character):
        return is_affordable(self.cost, dice, character)
    """
    
    def _get_action_prefix(self, deck):
        if 'food' in self.tags:
            # if someone has full health, he/she still can be healed, which is different from the original game
            return [f'action {self.code_name} {cha.code_name}' for cha in deck.characters if cha.hungry]
        return f'action {self.code_name}'
    
    def get_action_space(self, deck):
        res = generate_action_space(self.cost, deck.current_dice, deck.get_current_character(), prefix=self._get_action_prefix(deck))
        if count_total_dice(deck.current_dice) > 0:
            for i in deck.current_dice:
                if deck.current_dice[i] > 0:
                    res.append(f'convert {self.code_name};cost 1 {i};gen 1 {deck.get_current_element()}')
        return res
    
    def state(self):
        return vars(self)
    
    def __repr__(self):
        return f"{self.name}: {self.des}"

def init_actions(names):
    # assert len(names) == 30
    pool = load_js('Actions')
    
    """
    for i in pool:
        i['code_name'] = to_code_name(i['name'])
    dump_js('Actions.json', pool)
    """
    
    return [Action(name, pool) for name in names]
    
        
