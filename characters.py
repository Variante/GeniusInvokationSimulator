from utils import *

class Character:
    def __init__(self, name, pool):
        for i in pool:
            if i['name'] == name:
                data = i
                break
        else:
            print(f'Unknown character {name}.')
            exit(0)
            
        self.name = name
        self.skill = data['skill']
        self.health = data.get('health', 10)
        self.health_limit = data.get('health_limit', 10)
        self.power = 0
        self.power_limit = data.get('power_limit', 3)
        self.main_element = data.get('element', 'Pyro')
        
        self.weapon = None
        self.artifact = None
        self.equip = None
        
        self.attached_element = None
        self.frozen = False
        self.not_hungry = False
        self.active = False
        self.activate_cost = 1
        
        self.alive = True

    
    def affordable_skills(self, dice):
        res = []
        for skill in self.skill:
            if 'cost' in skill:
                res.extend(generate_action_space(skill['cost'], dice, self, prefix=f'action skill {skill["name"]}'))
        return res
        
    def get_action_space(self, deck):
        if not self.alive or self.frozen:
            return []
        res = self.affordable_skills(deck.current_dice)
        if not self.active:
            res.extend(generate_action_space(build_cost(self.activate_cost), deck.current_dice,
            self, prefix=f'activate {self.name}'))
        return res


    def state(self):
        return vars(self)
        
    def __repr__(self):
        return json.dumps(self.state())
        

def init_characters(names):
    # assert len(set(names)) == 3
    pool = load_js('Characters')
    res = [Character(name, pool) for name in names]
    res[0].active = True
    return res
    
        
