from utils import *

class Skill:
    def __init__(self, data):
        self.name = data['name']
        self.code_name = data['code_name']
        self.stype = data['type']
        self.cost = data['cost']
        self.des = data['des']

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
        self.code_name = data['code_name']
        self.skills = [Skill(i) for i in data['skills']]
        self.health = data.get('health', 5)
        self.health_limit = data.get('health_limit', 10)
        self.power = 3
        self.power_limit = data.get('power_limit', 3)
        self.main_element = data.get('element', 'Pyro')
        
        self.weapon = None
        self.artifact = None
        self.equip = None
        
        self.attached_element = None
        self.frozen = False
        self.hungry = True
        self.active = False
        self.activate_cost = 1
        
        self.alive = True

    
    def affordable_skills(self, dice):
        res = []
        for skill in self.skills:
            res.extend(generate_action_space(skill.cost, dice, self, prefix=f'skill {self.code_name} {skill.code_name}'))
        return res
        
    def get_action_space(self, deck):
        if not self.alive or self.frozen:
            return []
        res = self.affordable_skills(deck.current_dice)
        if not self.active:
            res.extend(generate_action_space(build_cost(self.activate_cost), deck.current_dice,
            self, prefix=f'activate {self.name}'))
        return res
    
    def on_round_finished(self):
        self.alive = self.health != 0
        self.frozen = False
        self.hungry = True

    def heal(self, num):
        self.health = min(num + self.health, self.health_limit)
        
    def dmg(self, num):
        self.health = max(self.health - num, 0)
        # dead
        if self.health == 0:
            self.weapon = None
            self.artifact = None
            self.equip = None
            
            self.attached_element = None
            self.frozen = False
            self.hungry = True
            self.active = False
            self.activate_cost = 1e9
            
            self.alive = False

    def state(self):
        return vars(self)
        
    def __repr__(self):
        return f"{self.name}{'<*>'if self.active else ''} - H: {self.health}\n" + \
               f"Debuffs: {'[Full]' if not self.hungry else ''}{'[Frozen]' if self.frozen else ''}\n" + \
               f"W: {'[W]' if self.weapon else ''} A: {'[A]' if self.artifact else ''} E: {'[E]' if self.equip else ''}\n" + \
               f"Main element: {self.main_element:<5} | Attached element: {' '.join(self.attached_element) if self.attached_element else ''}"
        

def init_characters(names):
    # assert len(set(names)) == 3
    pool = load_js('Characters')
    
    """
    for i in pool:
        i['code_name'] = to_code_name(i['name'])
        
        for j in i['skills']:
            j['code_name'] = to_code_name(j['name'])
    dump_js('Characters.json', pool)
    """
    res = [Character(name, pool) for name in names]
    res[0].active = True
    return res
    
        
