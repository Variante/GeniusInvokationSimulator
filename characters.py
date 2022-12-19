from utils import *

class Skill:
    def __init__(self, data):
        self.name = data['name']
        self.code_name = data['code_name']
        self.stype = data['type']
        self.cost = data['cost']
        self.des = data['des']


class Buff:
    def __init__(self, source, code):
        self.source = source
        self.code = code
        self.life = 1
        self.rf_by_round = 1 # life reduced per round
        self.rf_by_activated = 1 # life reduced by activated
        self.attribs = {}
        self.parse_code(code)

    def parse_code(self, code):
        cmds = code.split(',')
        for cmd in cmds:
            cmdw = cmd.split()
            if cmdw[0] == 'life':
                self.life = int(cmdw[1])
                self.rf_by_round = int(cmdw[2])
                self.rf_by_activated = int(cmdw[3])
                
            elif cmdw[0] == 'buff':
                try:
                    self.attribs[cmdw[1]] = int(cmdw[2])
                except IndexError:
                    self.attribs[cmdw[1]] = 1
                
    def get_attribs(self):
        return self.attribs

    def on_activated(self):
        self.life -= self.rf_by_activated
        
    def on_round_finished(self):
        self.life -= self.rf_by_round

    def __repr__(self):
        attribs = ','.join([f'{i}({self.attribs[i]})' for i in self.attribs])
        return f"[{attribs} from {self.source} ({self.life})]"

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
        self.buffs = []
        
        
        self.attached_element = None
        self.active = False
        self.activate_cost = 1
        
        self.alive = True

    
    
    def affordable_skills(self, dice):
        res = []
        for skill in self.skills:
            res.extend(generate_action_space(skill.cost, dice, self, prefix=f'skill {self.code_name} {skill.code_name}'))
        return res
        
    def get_action_space(self, deck):
        if not self.alive:
            return []
        if self.query_buff('frozen'):
            return []
        res = self.affordable_skills(deck.current_dice)
        if not self.active:
            res.extend(generate_action_space(build_cost(self.activate_cost), deck.current_dice,
            self, prefix=f'activate {self.name}'))
        return res
    
    def query_buff(self, keyword):
        value = 0
        for i in self.buffs:
            value += i.get_attribs().get(keyword, 0)
        return value
        
    def take_buff(self, keyword):
        value = 0
        for i in self.buffs:
            v = i.get_attribs().get(keyword, 0)
            if v > 0:
                i.on_activated()
                value += v
        self.refresh_buffs()
        return value
    
    def refresh_buffs(self):
        self.buffs = [buff for buff in self.buffs if buff.life > 0]
    
    def on_round_finished(self):
        for i in self.buffs:
            i.on_round_finished()
        self.refresh_buffs()

    def add_buff(self, name, code):
        if isinstance(code, str):
            self.buffs.append(Buff(name, code))
        else:
            raise NotImplementedError('Unknown buff code format')

    def frozen(self):
        self.add_buff('frozen', 'life 1 1 0')
        
    def heal(self, num):
        self.health = min(num + self.health, self.health_limit)
        
    def dmg(self, num):
        d = self.take_buff('shield')
        num = max(num - d, 0)
        
        self.health = max(self.health - num, 0)
        # dead
        if self.health == 0:
            self.weapon = None
            self.artifact = None
            self.equip = None
            
            self.attached_element = None
            self.buffs = []
            self.active = False
            self.activate_cost = 1e9
            
            self.alive = False

    def state(self):
        return vars(self)
        
    def __repr__(self):
        return f"{self.name} ({self.health}) {'<*>'if self.active else ''}\n" + \
               f"Buffs: {''.join([buff.__repr__() for buff in self.buffs])}\n" + \
               f"W: {'[W]' if self.weapon else ''} |A: {'[A]' if self.artifact else ''} |E: {'[E]' if self.equip else ''}\n" + \
               f"Main element: {self.main_element:<5} | Attached element: {' '.join(self.attached_element) if self.attached_element else ''}"
        

def init_characters(names):
    # assert len(set(names)) == 3
    pool = load_js('Characters')
    
    chrs = set()
    save = False
    for i in pool:
        chrs.add(i['name'])
        if 'code_name' not in i:
            save = True
            i['code_name'] = to_code_name(i['name'])
        
        for j in i['skills']:
            if 'code_name' not in j:
                save = True
                j['code_name'] = to_code_name(j['name'])
    if save:
        dump_js('Characters.json', pool)
    
    print('Available characters: ', chrs)
    
    res = [Character(name, pool) for name in names]
    res[0].active = True
    return res
    
        
