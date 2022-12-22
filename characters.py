from utils import *
from buff import Buff, Weapon, Artifact

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

        # special code for ellin
        if self.round_usage == 1:
            for s in my_deck.supports:
                if s.code_name == 'ellin':
                    s.on_activated()


        self.round_usage += 1
        if my_char.talent:
            self.round_usage_with_talent += 1

        energy_gain = 1 if self.stype != 'elemental_burst' else 0

        weapon =  my_char.weapon

        dealt_dmg = 0
        dmg_type = None
        reaction = False

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
                
                if weapon is not None:
                    dmg += 1
                    if enemy_char.health <= 6:
                        dmg += my_char.weapon.query('enemy_health_lower_than_six_dmg_up')
                # query all buffs
                res = my_char.take_pattern_buff(self.stype)
                for i in res:
                    if 'dmg_up' in i:
                        dmg += res[i]
                        
                dealt_dmg, reaction = enemy_char.take_dmg(dmg_type, dmg, 'e_' + self.code_name)

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
                dealt_dmg, reaction = my_char.take_dmg(cmds[1], 0, 'm_' + self.code_name)
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

        # gen die based on the weapon
        if self.stype == 'elemental_skill' and weapon is not None:
            v = weapon.query('gen_current_die')
            if v > 0:
                my_deck.cost(my_char.element, -v) # generate dices
                weapon.on_activated()

        my_char.proc_buff_event(f'on_{self.stype}_finished')

        enemy_char.proc_buff_event('on_enemy_skill_finished')

        if my_char.query_buff('on_skill_finished'):
            if my_char.take_buff('switch_my_prev'):
                my_deck.activate_prev()


        def calculate_chang(deck):
            i = 0
            l = deck.supports
            while True:
                try:
                    s = l[i]
                except IndexError:
                    break
                if s.code_name == 'chang_the_ninth':
                    s.on_activated()
                    if s.life == 0:
                        l.pop(i)
                        deck.pull(2)
                        continue
                i += 1
                    
        # chang_the_ninth
        if dealt_dmg > 0 or reaction:
            calculate_chang(my_deck)
            calculate_chang(my_deck.enemy_ptr)

        def calculate_parametric_transformer(deck):
            i = 0
            l = deck.supports
            while True:
                try:
                    s = l[i]
                except IndexError:
                    break
                if s.code_name == 'parametric_transformer':
                    s.on_activated()
                    if s.life == 0:
                        deck.get_current_character()._engine_buff(s)
                        l.pop(i)
                        continue
                i += 1
        # parametric_transformer
        if dmg_type is not None and dmg_type != 'Physical':
            calculate_parametric_transformer(my_deck)
            calculate_parametric_transformer(my_deck.enemy_ptr)

    def get_cost(self, deck, char):
        mods = char.query_pattern_buff(self.stype)
        if self.round_usage == 1:
            for i in deck.supports:
                if i.code_name == 'ellin':
                    kw = f'{self.stype}_cost_{to_code_name(char.element)}_down'
                    mods[kw] = mods.get(kw, 0) + 1

        return modify_cost(self.cost, mods)

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
        self.energy_limit = data['energy_limit']
        self.energy = 0
        self.element = data['element']
        
        self.faction = data['faction']
        self.weapon_type = data['weapon']
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

    def _update_save(self, cost, tp):
        kw = f'{tp}_save'
        for s in self.deck_ptr.supports:
            res = s.query(kw)
            if res >= cost:
                s.on_activated()
                s.change_keyword(kw, res - cost)
                break

    def add_weapon(self, action, data):
        self.weapon = Weapon(action.code_name, data, self, self.weapon_type)
        self._update_save(action.cost['d_num'][0], 'weapon')

    def add_artifact(self, action, data):
        self.artifact = Artifact(action.code_name, data, self)
        self._update_save(action.cost['d_num'][0], 'artifact')

    def add_shield(self, source, strength):
        self.add_buff(source, f'shield {strength}')
    
    def proc_buff_event(self, keyword):
        for buff in self.get_buff(keyword):
            self._engine_buff(buff)

    def _engine_buff(self, buff):
        activated = False

        res = buff.query('dmg')
        if isinstance(res, tuple) and res[1] > 0:
            activated = True
            self.deck_ptr.get_enemy_current_character().take_dmg(res[0], res[1], 'e_' + self.code_name)

        res = buff.query('heal')
        if res > 0:
            activated = True
            self.heal(res)

        res = buff.query('heal_injured_bg_most')
        if res > 0:
            activated = True
            injured_val = -1
            injured_char = None
            for c in self.deck_ptr.get_other_characters():
                if c.get_health_need() > injured_val:
                    injured_val = c.get_health_need()
                    injured_char = c
            if injured_char is not None:
                injured_char.heal(res)
         
        res = buff.query('gen_Omni')
        if res > 0:
            activated = True
            self.deck_ptr.cost('Omni' , -res)

        res = buff.query('gen_Rand')
        if res > 0:
            activated = True
            self.deck_ptr.cost(self.deck_ptr.d.random_type() , -res)

        res = buff.query('gen_current')
        if res > 0:
            activated = True
            self.deck_ptr.cost(self.element, -res)

        res = buff.query('heal_all')
        if res > 0:
            activated = True
            for c in self.deck_ptr.get_alive_characters():
                c.heal(res)

        res = buff.query('recharge')
        if res > 0:
            activated = self.deck_ptr.recharge(['recharge', 'active', res])

        res = buff.query('recharge_any')
        if res > 0:
            activated = self.deck_ptr.recharge(['recharge', 'any', res])

        res = buff.query('recharge_bg')
        if res > 0:
            activated = True
            for c in self.deck_ptr.get_other_characters():
                c.recharge(res)
        
        res = buff.query('draw')
        if res > 0:
            activated = True
            self.deck_ptr.pull(res)

        res = buff.query('draw_food')
        if res > 0:
            activated = True
            self.deck_ptr.pull_one_food(res)

        if activated:
            buff.on_activated()


    def affordable_skills(self, dice):
        res = []
        for skill in self.skills:
            res.extend(
                generate_action_space(skill.get_cost(self.deck_ptr, self),
                dice, self, prefix=f'skill {self.code_name} {skill.code_name}'))
        return res
        
    def get_action_space(self, deck):
        if not self.alive:
            return []
        if self.query_buff('frozen'):
            return []
        return self.affordable_skills(deck.current_dice)
    
    def _get_buff_list(self):
        res = []
        if self.weapon:
            res.append(self.weapon)
        if self.artifact:
            res.append(self.artifact)
        return self.buffs + res

    def get_buff(self, keyword):
        return [i for i in self._get_buff_list() if i.query(keyword)]
        
    def query_buff(self, keyword):
        value = 0
        for i in self._get_buff_list():
            value += i.query(keyword)
        return value
    
    def query_pattern_buff(self, buff_head):
        res = {}
        for i in self._get_buff_list():
            for j in i.attribs:
                if j.startswith(buff_head):
                    res[j] = i.query(j)
        return res

    def take_buff(self, keyword):
        value = 0
        for i in self._get_buff_list():
            res= i.query(keyword)
            if res > 0:
                value += res
                i.on_activated()
        self.refresh_buffs()
        return value

    def take_buff_until(self, keyword, need):
        value = 0
        for i in self._get_buff_list():
            res= i.query(keyword)
            if res > 0:
                value += res
                i.on_activated()
                if value >= need:
                    break
        self.refresh_buffs()
        return value

    def take_pattern_buff(self, buff_head):
        res = {}
        for i in self._get_buff_list():
            activated = False
            for j in i.attribs:
                if j.startswith(buff_head) and i.query(j) > 0:
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

        self.proc_buff_event('on_character_activated')

    def deactivate(self):
        transfer_buff = []
        for i in range(len(self.buffs) - 1, -1, -1):
            if self.buffs[i].query('transfer'):
                transfer_buff.append(self.buffs.pop(i))
        self.active = False
        # return transfer_buff
        self.deck_ptr.transfer_buff.extend(transfer_buff)

    def on_defeated(self):
        self.proc_buff_event('on_defeated')
        self.deck_ptr.defeated_this_round += 1
        self.weapon = None
        self.artifact = None
        self.equip = None
        
        self.infusion_element = []
        self.buffs = []
        self.active = False
        self.activate_cost = 100
        self.alive = False

    def on_round_finished(self):
        self.proc_buff_event('on_round_finished')
        
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
        
        reaction = False
        if dmg_type != 'Physical':
            reaction = self.infusion(dmg_type, source)
        
        return self.dmg(dmg_num, 0), reaction
        
    def dmg(self, dmg_num, dmg_no_shield):
        v = self.take_buff('vulnerable')
        dmg_num += v
        # This video is about how to calculate the shield
        # https://www.bilibili.com/video/BV1384y1t7cE/

        # move transfer buffs to the end
        self.buffs.sort(key=lambda x: x.query('transfer'))
        i = 0
        while dmg_num > 0 and i < len(self.buffs):
            buff = self.buffs[i]
            res = buff.query('dmg_down')
            if res > 0:
                dmg_num -= res
                buff.on_activated()

            if dmg_num <= 0:
                break

            res = buff.query('shield')
            if res > 0:
                if dmg_num >= res:
                    buff.change_keyword('shield', 0)
                else:
                    buff.change_keyword('shield', res - dmg_num)
                    break                
            i += 1
        """
        if dmg_num > 0:
            d = self.take_buff('dmg_down')
            dmg_num = max(dmg_num - d, 0)
        
        if dmg_num >= self.shield:
            dmg_num -= self.shield
            self.shield = 0
        else:
            self.shield -= dmg_num
        """

        self.health = max(self.health - dmg_num - dmg_no_shield, 0)
        # dead
        if self.health == 0:
            self.deactivate()
            self.on_defeated()
        # return the total damage caused
        return dmg_num + dmg_no_shield

    def melt_or_vaporize(self, reaction):
        self.add_buff(f'reaction_{reaction}', 'vulnerable 2')
        
    def overloaded(self):
        self.add_buff(f'reaction_overloaded', 'vulnerable 2')
        if self.active:
            self.deck_ptr.activate_next()
    
    def swirl(self, element, source):
        # print('\n\n swirl element ', element)
        for c in self.deck_ptr.get_other_characters():
            """
            # add swirl dmg to buff
            c.add_buff(f'reaction_swirl_{element}', 'vulnerable 1')
            # attach new element and calculate dmg
            c.take_dmg(element, 0)
            """
            c.take_dmg(element, 1, source)
        
        # swirl for the large wind spirit
        for i in self.deck_ptr.enemy_ptr.get_summon_buff('on_swirl'):
            i.remove_keyword('on_swirl')
            dtype, dval = i.query('dmg')
            assert dtype == 'Anemo'
            i.change_keyword('dmg', (element, dval))
    
    def frozen(self):
        self.add_buff('reaction_frozen', 'frozen')

    def infusion(self, element, source):
        if element in self.infusion_element:
            return False
        for t, i in enumerate(self.infusion_element):
            reaction = element_can_react(i, element)
            if reaction:
                enemy_char = self.deck_ptr.get_enemy_current_character()

                # if anyone triggers a reaction
                self.proc_buff_event('on_reaction')
                enemy_char.proc_buff_event('on_reaction')

                # for card "Elemental Resonance: Fervent Flames"
                if 'Pyro' in [i, element] and source == 'e_' + enemy_char.code_name:
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
                    self.swirl(i, source)
                else:
                    # TODO: add reaction later
                    raise NotImplementedError(f'no reaction implemented {i} vs {element} - ')
                try:
                    self.infusion_element = self.infusion_element[:t] + self.infusion_element[t + 1:]
                except IndexError:
                    self.infusion_element = self.infusion_element[:t]
                return True
        if element not in ['Geo', 'Anemo']:
            self.infusion_element.append(element)
        return False

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
            'faction': self.faction,
            'weapon_type': self.weapon_type,
            
            'weapon': self.weapon.state() if self.weapon else None,
            'artifact': self.artifact.state() if self.artifact else None,
            'talent': self.talent,
            
            'buffs': [i.state() for i in self.buffs],
            
            'infusion_element': self.infusion_element,
            'active': self.active,
            'activate_cost': self.activate_cost,
            'alive': self.alive
        }
        
    def __repr__(self):
        return f"{self.name} | H: {self.health} / {self.health_limit} | E: {self.energy} / {self.energy_limit} {'| <*>'if self.active else ''}\n" + \
               f"Buffs: {''.join([buff.__repr__() for buff in self.buffs])}\n" + \
               f"T: {self.talent:<5} {('W: ' + self.weapon.name) if self.weapon else ''} {('A: ' + self.artifact.name) if self.artifact else ''}\n" + \
               f"E: {self.element:<5} | {' '.join(self.infusion_element)}"
        
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


