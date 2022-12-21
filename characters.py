from utils import *
from buff import Buff

class Skill:
    def __init__(self, data):
        self.name = data['name']
        self.code_name = data['code_name']
        self.stype = to_code_name(data['type'])
        self.cost = data['cost']
        self.des = data['des']
        self.code = data['code'].split(';')
        self.round_usage = 0
        self.round_usage_with_talent = 0
        
    def exec(self, my_deck, my_char, enemy_char):
        self.round_usage += 1
        if my_char.talent:
            self.round_usage_with_talent += 1

        energy_gain = 1 if self.stype != 'elemental_burst' else 0

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
                dmg = int(cmds[2])
                
                # query all buffs
                res = my_char.take_pattern_buff(self.stype)
                for i in res:
                    if 'dmg_up' in i:
                        dmg += res[i]
                        
                enemy_char.take_dmg(dmg_type, dmg, self.code_name)
                """
                if self.stype == "normal_attack":
                    dmg += my_char.take_pattern_buff("normal_attack_dmg_up")
                    my_char.take_buff("normal_attack_cost_unaligned_down")
                elif self.stype == "elemental_burst"
                    dmg += my_char.take_buff("elemental_burst_dmg_up")
                """
            elif cmds[0] == 'heal':
                h = int(cmds[1])
                # query all buffs
                res = my_char.take_pattern_buff(self.stype)
                for i in res:
                    if 'heal_up' in i:
                        h += res[i]
                my_char.heal(h)

            elif cmds[0] == 'energy':
                energy_gain = int(cmds[1])
            elif cmds[0] == 'infusion':
                my_char.take_dmg(cmds[1], 0, self.code_name)
            elif cmds[0] == 'buff':
                my_char.add_buff(f'skill {my_char.name}-{self.code_name}', code)
            elif cmds[0] == 'summon':
                my_deck.add_summon(f'skill {my_char.name}-{self.code_name}', cmds[1])
            elif cmds[0] == 'switch_enemy':
                deck = my_deck.enemy_ptr
                if cmds[1] == 'prev':
                    deck.activate_prev()
                else:
                    deck.activate_next()
            else:
                raise NotImplementedError(f'[{self.name}] exec {self.code} - {code}')
                
        my_char.recharge(energy_gain)

        if my_char.query_buff('on_skill_finished'):
            if my_char.take_buff('switch_my_prev'):
                my_deck.activate_prev()


    def get_cost(self, my_char):
        cost = self.cost 
        return cost

    def on_round_finished(self):
        self.round_usage = 0
        self.round_usage_with_talent = 0
        
    def state(self):
        return vars(self)
        
    def __repr__(self):
        return json.dumps(self.state())
        

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
        self.health_limit = data.get('health_limit', 10)
        self.health = self.health_limit
        self.energy_limit = data.get('energy_limit', 3)
        self.energy = self.energy_limit # 0
        self.element = data.get('element', 'Pyro')
        
        self.weapon = None
        self.artifact = None
        self.talent = False
        self.buffs = []
        
        
        self.infusion_element = []
        self.active = False
        self.activate_cost = 1    
        self.alive = True
        
        self.deck_ptr = None

    def add_talent(self, talent):
        self.talent = True

    def engine_buff(self, buff):
        activated = False

        res = buff.query('dmg')
        if isinstance(res, tuple) and res[1] > 0:
            activated = True
            self.deck_ptr.get_enemy_current_character().take_dmg(res[0], res[1], buff.source)

        res = buff.query('heal')
        if res > 0:
            activated = True
            self.heal(res)
            
        if activated:
            buff.on_activated()


    def affordable_skills(self, dice):
        res = []
        for skill in self.skills:
            mods = self.query_pattern_buff(skill.stype)
            res.extend(
                generate_action_space(modify_cost(skill.get_cost(self), mods),
                dice, self, prefix=f'skill {self.code_name} {skill.code_name}'))
        return res
        
    def get_action_space(self, deck):
        if not self.alive:
            return []
        if self.query_buff('frozen'):
            return []
        return self.affordable_skills(deck.current_dice)
    
    def get_buff(self, keyword):
        return [i for i in self.buffs if i.query(keyword)]
        
    def query_buff(self, keyword):
        value = 0
        for i in self.buffs:
            value += i.query(keyword)
        return value
    
    def query_pattern_buff(self, buff_head):
        res = {}
        for i in self.buffs:
            for j in i.attribs:
                if j.startswith(buff_head):
                    res[j] = i.query(j)
        return res

    def take_buff(self, keyword):
        value = 0
        for i in self.buffs:
            if keyword in i.attribs:
                i.on_activated()
                value += i.query(keyword)
        self.refresh_buffs()
        return value

    def take_pattern_buff(self, buff_head):
        res = {}
        for i in self.buffs:
            activated = False
            for j in i.attribs:
                if j.startswith(buff_head):
                    activated = True
                    res[j] = i.query(j)
            if activated:
                i.on_activated()
        self.refresh_buffs()
        return res
    
    def refresh_buffs(self):
        self.buffs = [buff for buff in self.buffs if buff.life > 0]
    
    def activate(self):
        # self.buffs.extend(buffs)
        self.active = True
        self.buffs.extend(self.deck_ptr.transfer_buff)
        self.deck_ptr.transfer_buff = []
        
        for buff in self.get_buff('on_character_activated'):
            self.engine_buff(buff)

    def deactivate(self):
        transfer_buff = []
        for i in range(len(self.buffs) - 1, -1, -1):
            if self.buffs[i].query('transfer'):
                transfer_buff.append(self.buffs.pop(i))
        self.active = False
        # return transfer_buff
        self.deck_ptr.transfer_buff.extend(transfer_buff)

    def on_dead(self):
        self.weapon = None
        self.artifact = None
        self.equip = None
        
        self.infusion_element = []
        self.buffs = []
        self.active = False
        self.activate_cost = 100
        self.alive = False

    def on_round_finished(self):
        for buff in self.get_buff('on_round_finished'):
            self.engine_buff(buff)
        
        for i in self.skills:
            i.on_round_finished()
        
        for i in self.buffs:
            i.on_round_finished()
        self.refresh_buffs()

    def add_buff(self, source, code):
        if isinstance(code, str):
            self.buffs.append(Buff(source, code, self))
        else:
            raise NotImplementedError('Unknown buff code format')
    
    def get_health_need(self):
        return self.health_limit - self.health

    def get_energy_need(self):
        return self.energy_limit - self.energy
    
    def recharge(self, gain):
        self.energy = max(min(self.energy + gain, self.energy_limit), 0)
    
    def heal(self, num):
        self.health = min(num + self.health, self.health_limit)
        
    def take_dmg(self, dmg_type, dmg_num, source):
        if dmg_type in ['Physical', 'Pyro']:
            if self.take_buff('frozen'):
                self.add_buff(f'reaction_unfrozen', 'vulnerable 2')
            
        if dmg_type != 'Physical':
            self.infusion(dmg_type, source)
        
        self.dmg(dmg_num)
        
    def dmg(self, num):
        v = self.take_buff('vulnerable')
        num += v
        if num > 0:
            d = self.take_buff('shield')
            num = max(num - d, 0)
        
        self.health = max(self.health - num, 0)
        # dead
        if self.health == 0:
            self.deactivate()
            self.on_dead()

    def melt_or_vaporize(self, reaction):
        self.add_buff(f'reaction_{reaction}', 'vulnerable 2')
        
    def overloaded(self):
        self.add_buff(f'reaction_overloaded', 'vulnerable 2')
        if self.active:
            self.deck_ptr.activate_next()
    
    def swirl(self, element):
        # print('\n\n swirl element ', element)
        for c in self.deck_ptr.get_other_characters():
            """
            # add swirl dmg to buff
            c.add_buff(f'reaction_swirl_{element}', 'vulnerable 1')
            # attach new element and calculate dmg
            c.take_dmg(element, 0)
            """
            c.take_dmg(element, 1, 'swirl')
        
        # swirl for the large wind spirit
        for i in self.deck_ptr.enemy_ptr.get_summon_buff('on_swirl'):
            i.remove_keyword('on_swirl')
            dtype, dval = i.query('dmg')
            i.change_keyword('dmg', (element, dval))
    
    def frozen(self):
        self.add_buff('reaction_frozen', 'frozen')

    def infusion(self, element, source):
        if element in self.infusion_element:
            return
        for t, i in enumerate(self.infusion_element):
            reaction = element_can_react(i, element)
            if reaction:
                enemy_char = self.deck_ptr.get_enemy_current_character()
                if 'Pyro' in [i, element] and source == enemy_char.code_name:
                    val = enemy_char.take_buff(f'pyro_reaction_dmg_up')
                    if val > 0:
                        self.add_buff(f'reaction_{reaction}', f'vulnerable {val}')
                        # TODO: not sure about this, should be good according to this video:
                        # https://www.bilibili.com/video/BV13P4y1X74c/
                    
                if reaction in ['melt' or 'vaporize']:
                    self.melt_or_vaporize(reaction)
                elif reaction == 'overloaded':
                    self.overloaded()
                elif reaction == 'swirl':
                    self.swirl(i)
                else:
                    # TODO: add reaction later
                    raise NotImplementedError(f'no reaction implemented {i} vs {element} - ')
                try:
                    self.infusion_element = self.infusion_element[:t] + self.infusion_element[t + 1:]
                except IndexError:
                    self.infusion_element = self.infusion_element[:t]
                return
        if element not in ['Geo', 'Anemo']:
            self.infusion_element.append(element)

    def state(self):
        return {
            'name': self.name,
            'code_name': self.code_name,
            'skills': [i.state() for i in self.skills],
            'health_limit': self.health_limit,
            'health': self.health,
            'energy_limit': self.energy_limit,
            'energy': self.energy,
            'element': self.element,
            
            'weapon': self.weapon,
            'artifact': self.artifact,
            'talent': self.talent,
            
            'buffs': [i.state() for i in self.buffs],
            
            'infusion_element': self.infusion_element,
            'active': self.active,
            'active_cost': self.activate_cost,
            'alive': self.alive
        }
        
    def __repr__(self):
        return f"{self.name} | H: {self.health} / {self.health_limit} | E: {self.energy} / {self.energy_limit} {'| <*>'if self.active else ''}\n" + \
               f"Buffs: {''.join([buff.__repr__() for buff in self.buffs])}\n" + \
               f"W: {'[W]' if self.weapon else ''} |A: {'[A]' if self.artifact else ''} |T: {self.talent}\n" + \
               f"Element: {self.element:<5} | Infusion element: {' '.join(self.infusion_element)}"
        
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
    
    return [Character(name, pool) for name in names]
    
        
if __name__ == '__main__':
    print(json.dumps(init_characters(['Diluc'])[0].state()))


