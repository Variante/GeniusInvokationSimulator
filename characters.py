from utils import *

class Skill:
    def __init__(self, data):
        self.name = data['name']
        self.code_name = data['code_name']
        self.stype = data['type']
        self.cost = data['cost']
        self.des = data['des']
        self.code = data['code'].split(';')
        self.round_usage = 0        
        
    def exec(self, deck, my_char, enemy_char):
        self.round_usage += 1
        energy_gain = 1
        dmg=0
        dmg_type = 'Physical'
        
        for code in self.code:
            cmds = code.split()
            if cmds[0] == 'if_else':
                conds = code.split(':')
                if eval(conds[0].split()[1]):
                    code = conds[1]
                else:
                    code = conds[2]
                cmds = code.split()
            
            if cmds[0] == 'dmg':
                dmg_type = cmds[1]
                dmg += int(cmds[2])
            elif cmds[0] == 'energy':
                energy_gain = int(cmds[1])
            elif cmds[0] == 'infusion':
                my_char.infusion(cmds[1])
            else:
                raise NotImplementedError(f'[{self.name}] exec {self.code} - {code}')
        
        enemy_char.take_dmg(dmg, dmg_type)

    def on_round_finished(self):
        self.round_usage = 0


class Buff:
    def __init__(self, source, code):
        self.source = source
        self.code = code
        self.life = 1
        self.init_life = self.life 
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
                self.init_life = self.life 
            elif cmdw[0] == 'buff':
                try:
                    self.attribs[cmdw[1]] = int(cmdw[2])
                except IndexError:
                    self.attribs[cmdw[1]] = 1
                
    def get_attribs(self):
        return self.attribs
        
    def query(self, keyword):
        value = self.attribs.get(keyword, 0)
        if keyword.startswith('next') and self.life == self.init_life:
            value = 0
        return value

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
        self.energy = 3
        self.energy_limit = data.get('energy_limit', 3)
        self.main_element = data.get('element', 'Pyro')
        
        self.weapon = None
        self.artifact = None
        self.equip = None
        self.buffs = []
        
        
        self.infusion_element = []
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
            value += i.query(keyword)
        return value
        
    def take_buff(self, keyword):
        value = 0
        for i in self.buffs:
            v = i.query(keyword)
            if v > 0:
                i.on_activated()
                value += v
        self.refresh_buffs()
        return value
    
    def refresh_buffs(self):
        self.buffs = [buff for buff in self.buffs if buff.life > 0]
    
    def activate(self):
        self.active = True
    
    def on_dead(self):
        self.weapon = None
        self.artifact = None
        self.equip = None
        
        self.infusion_element = []
        self.buffs = []
        self.active = False
        self.activate_cost = 1e9
        self.alive = False
        
        """
        # request a character switch
        agent = self.deck.agent
        game = self.deck.game
        print("REQUEST change current agent: Player", game.current_agent + 1)
        # request current agent
        game.current_agent = game.agents.index(agent)
        print("REQUEST after change current agent: Player ", game.current_agent + 1)
        print(game.state())
        action = agent.get_action(game.state())
        game.parse_space_action(action)
        game.switch_agent = True
        """

        
    def on_round_finished(self):
        self.heal(self.take_buff('regain'))
        self.heal(self.take_buff('next_regain'))
        
        for i in self.skills:
            i.on_round_finished()
        
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
        
    def take_dmg(self, dmg, dmg_type):
        if dmg_type != 'Physical':
            self.infusion(dmg_type)
        self.dmg(dmg)
        
    def dmg(self, num):
        d = self.take_buff('shield')
        num = max(num - d, 0)
        
        self.health = max(self.health - num, 0)
        # dead
        if self.health == 0:
            self.on_dead()

    def infusion(self, element):
        for t, i in enumerate(self.infusion_element):
            if element_can_react(i, element):
                # TODO: add reaction later
                raise NotImplementedError(f'no reaction implemented {i} vs {element}')
                try:
                    self.infusion_element = self.infusion_element[:t] + self.infusion_element[t + 1:]
                except IndexError:
                    self.infusion_element = self.infusion_element[:t]
                return
        if element not in self.infusion_element:
            self.infusion_element.append(element)

    def state(self):
        return vars(self)
        
    def __repr__(self):
        return f"{self.name} ({self.health}) {'<*>'if self.active else ''}\n" + \
               f"Buffs: {''.join([buff.__repr__() for buff in self.buffs])}\n" + \
               f"W: {'[W]' if self.weapon else ''} |A: {'[A]' if self.artifact else ''} |E: {'[E]' if self.equip else ''}\n" + \
               f"Main element: {self.main_element:<5} | Infusion element: {' '.join(self.infusion_element)}"
        
    def get_skill(self, code_name):
        for i in self.skills:
            if i.code_name == code_name:
                return i
                
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
        dump_js('Characters', pool)
    
    print('Available characters: ', chrs)
    
    res = [Character(name, pool) for name in names]
    res[0].active = True
    return res
    
        
