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
        self.atype = data['type']
        
        if 'food' in self.tags:
            self.code += ';buff full'

        # self.active_character = data.get('active_character', None)
    """
    def is_affordable(self, dice, character):
        return is_affordable(self.cost, dice, character)
    """
    
    def _get_action_prefix(self, deck):
        if 'food' in self.tags:
            # if someone has full health, he/she still can be healed, which is different from the original game
            return [f'action {self.code_name} {cha.code_name}' for cha in deck.characters 
            if cha.query_buff('full') == 0 ]
            
        if 'switch_my' in self.code:
            return [f'action {self.code_name} {cha.code_name}' for cha in deck.get_other_characters() if cha.alive]
            
        if 'when_knocked_out' in self.tags and deck.kocked_out_this_round == 0:
            return []
            
        if 'recharge_active' in self.tags and deck.get_current_character().get_energy_need() < 1:
            return []
            
        if 'recharge_any' in self.tags:
            for cha in deck.characters:
                if cha.get_energy_need():
                    break
            else:
                return []
                
        if 'recharge_to' in self.tags:
            to_move = 0
            for cha in deck.get_other_characters():
                to_move += cha.energy
            if to_move == 0:
                return []
            if deck.get_current_character().get_energy_need() < 1:
                return []
            
            
            
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
        return f"- {self.name}: {self.des}"

def init_actions(names):
    # assert len(names) == 30
    pool = load_js('Actions')
    
    chrs = set()
    save = False
    for i in pool:
        chrs.add(i['name'])
        if 'code_name' not in i:
            save = True
            i['code_name'] = to_code_name(i['name'])
    if save:
        dump_js('Actions', pool)
        
    print('Available actions: ', chrs)
    return [Action(name, pool) for name in names]
    
        
