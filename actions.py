from utils import *

class Action:
    def __init__(self, name, pool):
        for i in pool:
            if i['name'] == name or i['code_name'] == name:
                data = i
                break
        else:
            print(f'Unknown action card {name}.')
            exit(0)
            
        self.name = data['name']   
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

        if self.atype == 'support':
            self.code = 'support ' +  self.code

    # Check whether we can use this card
    def _get_action_prefix(self, deck):
        my_char = deck.get_current_character()
        if self.atype == 'equipment':
            if 'talent' in self.tags:
                if my_char.code_name not in self.code and 'kamisato_ayaka' not in self.code:
                    return []
                if 'kamisato_ayaka' in self.code and deck.get_character('kamisato_ayaka') is None:
                    return []
                return f"event {self.code_name} {self.code.split(';')[0].split()[-1]}"
            elif 'weapon' in self.tags:
                return [f'event {self.code_name} {cha.code_name}' for cha in deck.get_alive_characters() if cha.weapon_type in self.tags]
            elif 'artifact' in self.tags:
                return [f'event {self.code_name} {cha.code_name}' for cha in deck.get_alive_characters()]
        elif self.atype == 'support':
            idx = len(deck.supports) # add to the end or replace the original one
            max_l = 4
            if idx < max_l:
                return [f'event {self.code_name} {idx}']
            else:
                return [f'event {self.code_name} {i}' for i in range(max_l)]
        else:
            if "tranfer_weapon" in self.tags:
                return [f'event {self.code_name} {i.code_name} {j.code_name}' for i in deck.get_alive_characters() for j in deck.get_alive_characters() if i.weapon is not None and i.weapon_type == j.weapon_type and i.code_name != j.code_name]
            if "tranfer_artifact" in self.tags:
                return [f'event {self.code_name} {i.code_name} {j.code_name}' for i in deck.get_alive_characters() for j in deck.get_alive_characters() if i.artifact is not None and i.code_name != j.code_name]

            if 'food' in self.tags:
                res = []
                for cha in deck.get_alive_characters():
                    if cha.query_buff('full'):
                        continue
                    if 'heal' in self.code and cha.get_health_need() > 0:                    
                        res.append(f'event {self.code_name} {cha.code_name}')
                return res

            if 'switch_my' in self.code:
                return [f'event {self.code_name} {cha.code_name}' for cha in deck.get_bg_characters() if cha.alive]
                
            if 'when_defeated' in self.tags and deck.defeated_this_round == 0:
                return []
                
            if 'recharge_active' in self.tags and my_char.get_energy_need() == 0:
                return []
                
            if 'recharge_any' in self.tags:
                for cha in deck.get_alive_characters():
                    if cha.get_energy_need() and cha.alive:
                        break
                else:
                    return []
                    
            if 'recharge_to_active' in self.tags:
                to_move = 0
                for cha in deck.get_bg_characters():
                    to_move += cha.energy
                if to_move == 0:
                    return []
                if my_char.get_energy_need() < 1:
                    return []

            if 'heal_summon' in self.code:
                if len(deck.summons) > 0:
                    return [f'event {self.code_name} {s.code_name}' for s in deck.summons]
                return []
                
            if 'kill_summon' in self.code:
                if len(deck.summons) > 0:
                    return [f'event {self.code_name} {s.code_name}' for s in deck.enemy_ptr.summons]
                return []

            if 'kill_all_summons' in self.code and (len(deck.summons) + len(deck.enemy_ptr.summons)) == 0:
                return []

            # every event must have a target
        return f'event {self.code_name} {my_char.code_name}'
    
    def get_cost(self, deck):
        # talent cost down by artifacts
        if 'talent' in self.tags:
            mods = deck.get_current_character().query_pattern_buff('talent')
            return modify_cost(self.cost, mods)
        # weapon/artifact/location cost down by supports
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
        # Use this card to generate 1 dice
        if count_total_dice(deck.current_dice) > 0:
            for i, j in deck.current_dice.items():
                if j > 0 and i not in [deck.get_current_element(), 'Omni']:
                    res.append(f'convert {self.code_name};cost {i} 1;gen {deck.get_current_element()} 1')
        return res
    
    def state(self):
        return {i:j for i, j in vars(self).items() if i not in ['des']}
    
    def __repr__(self):
        return f"- {self.name}" #: {self.des}"


class GenAction(Action):
    def __init__(self, code_name):
        pool = [{
            "img": "Lightning_Stiletto_Event_Card.webp",
            "name": "Lightning Stiletto",
            "cost_raw": "3 Electro Dices",
            "cost": {
                "d_type": [
                    "Electro"
                ],
                "d_num": [
                    3
                ],
                "p_num": 0
            },
            "des": "Combat Action: Switch your Keqing in to be your active character and immediately use Stellar Restoration once. This instance of Stellar Restoration will grant Keqing Electro Infusion without creating another Lightning Stiletto.\n(When Keqing uses Stellar Restoration with this card in Hand: Instead of creating another Lightning Stiletto, discard this card and Keqing gains Electro Infusion)",
            "code": "switch_my keqing;skill keqing stellar_restoration",
            "tags": ["generated", "talent"],
            "type": "equipment", # actually it is event but i'm lazy to change the code
            "code_name": "lightning_stiletto"
        }]
        super(GenAction, self).__init__(code_name, pool)


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
        
    # print('Available actions: ', chrs)
    return [Action(name, pool) for name in names]
    
        
if __name__ == '__main__':
    pool = load_js('Actions')
    l = [i['name'] for i in pool if 'TODO' not in i['tags']]
    print('Available actions: ', len(l))
    dump_js('test_action_list', l)
