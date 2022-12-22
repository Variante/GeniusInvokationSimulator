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
        self.code = data.get('code', '')
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
        elif 'weapon' in self.tags:
            self.code = 'weapon ' + self.code
        elif 'artifact' in self.tags:
            self.code = 'artifact ' + self.code

        # only available for support card
        # self.on_leave = data.get('on_leave', '')
        # self.active_character = data.get('active_character', None)
    """
    def is_affordable(self, dice, character):
        return is_affordable(self.cost, dice, character)
    """
    
    def _get_action_prefix(self, deck):
        if self.atype == 'equipment':
            if 'talent' in self.tags and deck.get_current_character().code_name not in self.code:
                return []
            elif 'weapon' in self.tags:
                return [f'equipment {self.code_name} {cha.code_name}' for cha in deck.get_alive_characters() if to_code_name(cha.weapon_type) in self.tags]
            elif 'artifact' in self.tags:
                return [f'equipment {self.code_name} {cha.code_name}' for cha in deck.get_alive_characters()]
            return f'equipment {self.code_name}'
        elif self.atype == 'support':
            idx = len(deck.supports) # add to the end or replace the original one
            max_l = 4
            if idx < max_l:
                res = [f'support {self.code_name} {idx}']
            else:
                res = [f'support {self.code_name} {i}' for i in range(max_l)]
            # this is for "knights_of_favonius_library"
            if 'reroll' in self.tags:
                return [f'{i};reroll 1' for i in res]
            return res
        else:
            if 'food' in self.tags:
                res = []
                for cha in deck.get_alive_characters():
                    if cha.query_buff('full'):
                        continue
                    if 'heal' in self.code and cha.get_health_need() > 0:                    
                        res.append(f'event {self.code_name} {cha.code_name}')
                return res

            if 'switch_my' in self.code:
                return [f'event {self.code_name} {cha.code_name}' for cha in deck.get_other_characters() if cha.alive]
                
            if 'when_defeated' in self.tags and deck.defeated_this_round == 0:
                return []
                
            if 'recharge_active' in self.tags and deck.get_current_character().get_energy_need() == 0:
                return []
                
            if 'recharge_any' in self.tags:
                for cha in deck.get_alive_characters():
                    if cha.get_energy_need() and cha.alive:
                        break
                else:
                    return []
                    
            if 'recharge_to_active' in self.tags:
                to_move = 0
                for cha in deck.get_other_characters():
                    to_move += cha.energy
                if to_move == 0:
                    return []
                if deck.get_current_character().get_energy_need() < 1:
                    return []

            if 'heal_summon' in self.code:
                if len(deck.summons) > 0:
                    return [f'event {self.code_name} {s.code_name}' for s in deck.summons]
                return []
                
            if 'kill_summon' in self.code:
                if len(deck.summons) > 0:
                    return [f'event {self.code_name} {s.code_name}' for s in deck.enemy_ptr.summons]
                return []

            if 'kill_all_summons' in self.code and len(deck.summons) + len(deck.enemy_ptr.summons) == 0:
                return []

            return f'event {self.code_name}'
    
    def get_cost(self, deck):
        if 'talent' in self.tags:
            mods = deck.get_current_character().query_pattern_buff('talent')
            return modify_cost(self.cost, mods)
        elif 'weapon' in self.tags:
            mods = deck.query_support_buff('weapon_save')
            if mods >= self.cost["d_num"][0]:
                return build_cost(0)
        elif 'artifact' in self.tags:
            mods = deck.query_support_buff('artifact_save')
            if mods >= self.cost["d_num"][0]:
                return build_cost(0)
        elif 'location' in self.tags:
            mods = deck.query_support_buff('location_save')
            if mods:
                return build_cost(self.cost["d_num"][0] - mods)
        return self.cost

    def get_action_space(self, deck):
        res = generate_action_space(self.get_cost(deck), deck.current_dice, deck.get_current_character(), prefix=self._get_action_prefix(deck))
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
    
        
if __name__ == '__main__':
    pool = load_js('Actions')
    dump_js('test_action_list', [i['name'] for i in pool])
