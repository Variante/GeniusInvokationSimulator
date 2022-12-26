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
        self.energy_gain = data.get('energy_gain', 1)
        if self.stype in ['elemental_burst', 'passive_skill']:
            self.energy_gain = 0
        # if one has talent
        self.code_talent = data.get('code_talent', data['code']).split(';')

        self.total_usage = 0
        self.round_usage = 0
        self.round_usage_with_talent = 0

    def reset(self):
        self.total_usage = 0
        self.round_usage = 0
        self.round_usage_with_talent = 0
        
    def exec(self, my_deck, my_char, enemy_char):
        self.total_usage += 1
        self.round_usage += 1
        if my_char.talent:
            self.round_usage_with_talent += 1

        my_char.recharge(self.energy_gain)
        weapon =  my_char.weapon

        dmg_type = 'Physical'
        dmg = 0
        reaction = False
        dealt_dmg = 0
        bc = 0
        for code in self.code_talent if my_char.talent else self.code:
            cmds = code.split()
            if cmds[0] == 'if_else':
                conds = code.split(':')
                if eval(conds[0].split()[1]):
                    code = conds[1]
                else:
                    code = conds[2]
                if len(code) == 0:
                    continue
                cmds = code.split()

            if cmds[0] == 'dmg':
                dmg_type = cmds[1]
                dmg = int(cmds[2])
                dmg_mods = 0
                if weapon is not None:
                    dmg_mods += 1
                    if enemy_char is not None and enemy_char.health <= 6:
                        dmg_mods += my_char.weapon.query('enemy_health_lower_than_six_dmg_up')

                # query all buffs
                for i, j in my_char.take_pattern_buff(self.stype).items():
                    if 'dmg_up' in i:
                        dmg_mods += j

                # query infusion
                if dmg_type == 'Physical':
                    for i in my_char.take_pattern_buff('infusion'):
                        if 'melee' in i and my_char.is_melee():
                            continue
                        dmg_type = i.split('_')[1]
                        break
                
                if enemy_char is None:
                    ddmg = 0
                    dreact = False
                else:
                    ddmg, dreact = enemy_char.take_dmg(dmg_type, dmg + dmg_mods, f'e-{my_char.code_name}-{self.code_name}')
                dealt_dmg += ddmg
                reaction |= dreact
            elif cmds[0] == 'dmg_bg':
                # all dmg to bg is Piercing
                for cha in my_deck.enemy_ptr.get_alive_characters():
                    ddmg, dreact = cha.take_dmg('Piercing', int(cmds[2]), f'e-{my_char.code_name}-{self.code_name}')
                    dealt_dmg += ddmg
                    reaction |= dreact
            elif cmds[0] == 'heal':
                h = int(cmds[1])
                # query all buffs
                """
                res = my_char.take_pattern_buff(self.stype)
                for i in res:
                    if 'heal_up' in i:
                        h += res[i]
                """
                my_char.heal(h)
            elif cmds[0] == 'heal_all':
                for c in my_deck.get_alive_characters():
                    c.heal(int(cmds[1]))
            elif cmds[0] == 'shield':
                my_char.add_shield(self, f'skill {my_char.name}-{self.code_name}', code)
            elif cmds[0] == 'buff':
                my_char.add_buff(f'skill {my_char.name}-{self.code_name}-{bc}', code + ',unique')
                bc += 1
            elif cmds[0] == 'summon':
                my_deck.add_summon(f'skill {my_char.name}-{self.code_name}', cmds[1], my_char.talent)
            elif cmds[0] == 'switch_enemy':
                my_deck.enemy_ptr.switch_next(cmds[1] == 'prev')
            elif cmds[0] == 'apply':
                my_char.attach_element_no_dmg(cmds[1])
            elif cmds[0] == 'recharge':
                my_deck.recharge(cmds)
            elif cmds[0] == 'gen_action':
                my_deck.gen_card(cmds[1])
            elif cmds[0] == 'drop_action':
                action = my_deck.use_card(cmds[1])
                my_deck.drop_card(action)
            else:
                raise NotImplementedError(f'[{self.name}] exec {self.code} - {code}')
        
        if self.stype == 'passive_skill':
            return

        # gen die based on the weapon
        if self.stype == 'elemental_skill' and weapon is not None:
            v = weapon.query('gen_current')
            if v > 0:
                my_deck.cost(my_char.element, -v) # generate dices
                weapon.on_activated()

        my_char.proc_buff_event(f'on_{self.stype}_finished')
        my_char.proc_buff_event(f'on_{my_char.code_name}_{self.stype}_finished') # for Fischl talent
        if enemy_char is not None:
            enemy_char.proc_buff_event('on_enemy_skill_finished')
        my_char.proc_buff_event('on_skill_finished')

        def move_progress(deck, kw):
            deck.activate_support_buffs(kw)
            deck.proc_support_buffs(kw)

        # special code for ellin
        if self.round_usage > 1:
            my_deck.proc_support_buffs('ellin')

        # chang_the_ninth
        if dealt_dmg > 0 or reaction:
            move_progress(my_deck, "chang_the_ninth")
            move_progress(my_deck.enemy_ptr, "chang_the_ninth")

        # parametric_transformer
        if dmg_type is not None and dmg_type not in ['Physical', 'Piercing']:
            move_progress(my_deck, 'parametric_transformer')
            move_progress(my_deck.enemy_ptr, 'parametric_transformer')


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
        
        self.faction = to_code_name(data['faction'])
        self.weapon_type = to_code_name(data['weapon'])
        self.weapon = None
        self.artifact = None
        self.talent = False
        self.buffs = []
        
        self.attached_element = []
        self.active = False
        self.activate_cost = 1    
        self.alive = True
        
        self.deck_ptr = None


    """
    Add equips
    
    """

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

    def add_shield(self, source, data):
        # for card "lithic_spear"
        faction = 'liyue'
        data = data.replace(faction, str(self.deck_ptr.count_character_by_faction(faction)))

        if 'team' in data:
            bl = self.deck_ptr.buffs
        else:
            bl = self.buffs

        for i, b in enumerate(bl):
            # refresh the shield
            if b.source == source: # buff from the same source should refresh the buff, i guess
                if source == 'crystallize':
                    # from reaction cystallize, stack up to 2
                    bl[i].change_keyword('shield', min(bl[i].query('shield') + 1, 2))
                else:
                    bl[i] = Buff(source, data, self)
                break
        else:
            bl.append(Buff(source, data, self))


    """
    process buff
    """
    def _get_buff_list(self):
        res = []
        if self.weapon:
            res.append(self.weapon)
        if self.artifact:
            res.append(self.artifact)
        return self.buffs + res + self.deck_ptr.buffs

    def add_buff(self, source, code):
        if isinstance(code, str):
            b = Buff(source, code, self)
            if 'team' in code:
                bl = self.deck_ptr.buffs
            else:
                bl = self.buffs
            if 'unique' in code:
                # replace the old buff
                for i, j in enumerate(bl):
                    if j.source == source:
                        bl[i] = b
                        return
            bl.append(b)

        else:
            raise NotImplementedError('Unknown buff code format')

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
                    res[j] = i.query(j) + res.get(j, 0)
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

    def take_pattern_buff(self, buff_head):
        res = {}
        for i in self._get_buff_list():
            activated = False
            for j in i.attribs:
                if j.startswith(buff_head) and i.query(j) > 0:
                    activated = True
                    res[j] = i.query(j) + res.get(j, 0)
            if activated:
                i.on_activated()
        self.refresh_buffs()
        return res
    
    def refresh_buffs(self):
        self.buffs = [buff for buff in self.buffs if not buff.should_leave()]
        self.deck_ptr.buffs = [buff for buff in self.deck_ptr.buffs if not buff.should_leave()]
    
    def proc_buff_event(self, keyword):
        for buff in self.get_buff(keyword):
            buff_engine(buff, self.deck_ptr, self.deck_ptr.enemy_ptr)


    """
    Get action space
    """
    def affordable_skills(self, dice):
        res = []
        for skill in self.skills:
            if skill.stype == 'passive_skill':
                continue
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
    
    """
    Switch character
    """
    
    def activate(self):
        self.active = True
        # redirect buffs
        for b in self.deck_ptr.buffs:
            b.char_ptr = self
        # activate passive skill
        for skill in self.skills:
            if skill.stype == 'passive_skill':
                skill.exec(self.deck_ptr, self, None)
        self.proc_buff_event('on_character_activated')

    def deactivate(self):
        self.active = False

    """
    Events
    """

    def on_defeated(self):
        self.proc_buff_event('on_defeated')
        self.deck_ptr.defeated_this_round += 1
        self.reset()
        self.alive = False

    def on_round_finished(self):
        self.proc_buff_event('on_round_finished')

        for i in self.skills:
            i.on_round_finished()
        for i in self.buffs:
            i.on_round_finished()
        self.refresh_buffs()

    """
    Get information and actions
    """
    def is_melee(self):
        return self.weapon_type in ['blade', 'claymore', 'polearm']
    
    def get_skill(self, code_name):
        for i in self.skills:
            if i.code_name == code_name:
                return i

    def get_health_need(self):
        return self.health_limit - self.health

    def get_energy_need(self):
        return self.energy_limit - self.energy
    
    def recharge(self, gain):
        activated = self.get_energy_need() > 0
        self.energy = max(min(self.energy + gain, self.energy_limit), 0)
        return activated
    
    def heal(self, num):
        activated = self.get_health_need() > 0
        self.health = min(num + self.health, self.health_limit)
        return activated
        
    def take_dmg(self, dmg_type, dmg_num, source, dmg_piercing=0):
        if dmg_type in ['Physical', 'Pyro']:
            if self.take_buff('frozen'):
                self.add_buff(f'{source}-unfrozen', 'vulnerable 2')

        if dmg_type in ['Pyro', 'Electro']:
            if self.deck_ptr.enemy_ptr.take_team_buff('dendro_core'):
                self.add_buff(f'{source}-dendro_core', 'vulnerable 2')

        if dmg_type in ['Dendro', 'Electro']:
            if self.deck_ptr.enemy_ptr.take_team_buff('catalyzing_field'):
                self.add_buff(f'{source}-catalyzing_field', 'vulnerable 1')
        
        reaction = self.attach_element(dmg_type, source)

        for i in self.deck_ptr.enemy_ptr.get_summon_buff(f'dmg_{dmg_type}_up'):
            self.add_buff(f'{i.source}-chaotic_entropy', f'vulnerable {i.query(f"dmg_{dmg_type}_up")}')
        
        return self.dmg(dmg_num, dmg_piercing, source), reaction
        
    def dmg(self, dmg_num, piercing_dmg, source):
        v = self.take_buff('vulnerable')
        dmg_num += v

        # This video is about how to calculate the shield
        # https://www.bilibili.com/video/BV1384y1t7cE/
        for buff in self.buffs + self.deck_ptr.buffs + self.deck_ptr.summons:
            res = buff.query('dmg_down') # purple buffs
            if res > 0:
                dmg_num -= 1
                buff.on_activated()

            if dmg_num <= 0:
                break

            res = buff.query('shield') # yellow buffs
            if res > 0:
                buff.on_activated() # for Lotus Flower Crisp
                if dmg_num >= res:
                    # remove this shield
                    dmg_num -= res
                    buff.life = 0
                else:
                    buff.change_keyword('shield', res - dmg_num)
        
            if dmg_num <= 0:
                break       

            # Xingqiu's skill: should use current dmg_num, from the same video above
            if dmg_num >= 3:
                res = buff.query('dmg_larger_than_three_dmg_down')
                if res > 0:
                    dmg_num -= 1
                    buff.on_activated()

            # Ningguang's skill: should use current dmg_num
            if dmg_num >= 2:
                res = buff.query('dmg_larger_than_two_dmg_down')
                if res > 0:
                    dmg_num -= 1
                    buff.on_activated()

    
        # TODO: buff from mona, double the real dmg (after shields) or raw dmg?:
        double = False
        enemy_deck = self.deck_ptr.enemy_ptr
        for c in enemy_deck.characters:
            if c.code_name in source:
                double = True
                break
        if double:
            if enemy_deck.take_team_buff('double_dmg_dealt'):
                dmg_num *= 2

        self.health = max(self.health - dmg_num - piercing_dmg, 0)
        # dead
        if self.health == 0:
            self.on_defeated()
        # return the total damage
        return dmg_num + piercing_dmg

    def melt_or_vaporize(self, source, reaction):
        self.add_buff(f'{source}-{reaction}', 'vulnerable 2')
        
    def overloaded(self, source):
        self.add_buff(f'{source}-overloaded', 'vulnerable 2')
        if self.active:
            self.deck_ptr.switch_next()

    def superconduct_or_electro_charged(self, source, reaction):
        self.add_buff(f'{source}-{reaction}', 'vulnerable 1')
        for c in self.deck_ptr.get_bg_characters():
            c.take_dmg('Piercing', 1, '{source}-{reaction}-piercing')
    
    def swirl(self, source, element):
        # print('\n\n swirl element ', element)
        for c in self.deck_ptr.get_bg_characters():
            c.take_dmg(element, 1, source + '-swirl')
        
        # swirl for the large wind spirit
        for i in self.deck_ptr.enemy_ptr.get_summon_buff('on_swirl'):
            i.remove_keyword('on_swirl')
            dtype, dval = i.query('dmg')
            assert dtype == 'Anemo'
            i.change_keyword('dmg', (element, dval))

            # for Chaotic Entropy card
            for cha in self.deck_ptr.enemy_ptr.get_alive_characters():
                if cha.code_name == 'sucrose' and cha.talent:
                    i.change_keyword(f'dmg_{element}_up', 1)
                    break

    def frozen(self, source):
        self.add_buff(source + '-frozen', 'frozen')

    def crystallize(self, source):
        self.add_buff(source + '-crystallize', 'vulnerable 1')

    def attach_element_no_dmg(self, element):
        if element in ['Physical', 'Piercing']:
            return False
        if element in self.attached_element:
            return False
        for t, i in enumerate(self.attached_element):
            reaction = element_can_react(i, element)
            if reaction:
                try:
                    self.attached_element = self.attached_element[:t] + self.attached_element[t + 1:]
                except IndexError:
                    self.attached_element = self.attached_element[:t]
                return True
        if element not in ['Geo', 'Anemo']:
            self.attached_element.append(element)
        return False

    def attach_element(self, element, source):
        # return whether there is an reaction or not
        if element in ['Physical', 'Piercing']:
            return False
        if element in self.attached_element:
            return False

        # When a card has both Cryo and Dendro statuses at the same time, 
        # if Electro/Hydro/Pyro are applied, the Cryo reaction will be triggered, 
        # and the Dendro application will remain unaffected.
        self.attached_element.sort()
        for t, i in enumerate(self.attached_element):
            reaction = element_can_react(i, element)
            if reaction:
                enemy_char = self.deck_ptr.get_enemy_current_character()

                # if anyone triggers a reaction
                self.proc_buff_event('on_reaction')
                if enemy_char is not None:
                    enemy_char.proc_buff_event('on_reaction')

                # for card "Elemental Resonance: Fervent Flames"
                if  enemy_char is not None and 'Pyro' in [i, element] and source.startswith('e-' + enemy_char.code_name):
                    val = enemy_char.take_buff(f'pyro_reaction_dmg_up')
                    if val > 0:
                        self.add_buff(f'{source}-{reaction}-dmg_up', f'vulnerable {val}')
                        # TODO: not sure about this, should be good according to this video:
                        # https://www.bilibili.com/video/BV13P4y1X74c/

                 # for card "Prophecy of Submersion"
                if  enemy_char is not None and 'Hydro' in [i, element]:
                    val = enemy_char.take_buff(f'hydro_reaction_dmg_up')
                    if val > 0:
                        self.add_buff(f'{source}-{reaction}-dmg_up', f'vulnerable {val}')

                if reaction in ['melt', 'vaporize']:
                    self.melt_or_vaporize(source, reaction)
                elif reaction == 'overloaded':
                    self.overloaded(source)
                elif reaction == 'swirl':
                    self.swirl(source, i)
                elif reaction in ['superconduct', 'electro_charged']:
                    self.superconduct_or_electro_charged(source, element)
                elif reaction == 'frozen':
                    self.frozen(source)
                elif reaction == 'crystallize':
                    self.crystallize(source)
                    if enemy_char is not None:
                        enemy_char.add_shield('crystallize', 'shield 1,team,life 2 0 0')
                elif reaction == 'bloom':
                    self.add_buff(f'{source}-{reaction}', 'vulnerable 1')
                    if enemy_char is not None:
                        enemy_char.add_buff(f'{source}-{reaction}', 'dendro_core,team,unique,life 1 0 1')
                elif reaction == 'quicken':
                    self.add_buff(f'{source}-{reaction}', 'vulnerable 1')
                    if enemy_char is not None:
                        enemy_char.add_buff(f'{source}-{reaction}', 'catalyzing_field,team,unique,life 3 0 1')
                elif reaction == 'burning':
                    self.add_buff(f'{source}-{reaction}', 'vulnerable 1')
                    for i in self.deck_ptr.enemy_ptr.summons:
                        if i.code_name == 'burning_flame' and i.life < 2:
                            i.life += 1
                            break
                    else:
                        self.deck_ptr.enemy_ptr.add_summon(f'{source}-{reaction}', 'burning_flame')
                else:
                    raise NotImplementedError(f'no reaction implemented {i} vs {element} - ')
                try:
                    self.attached_element = self.attached_element[:t] + self.attached_element[t + 1:]
                except IndexError:
                    self.attached_element = self.attached_element[:t]
                return True
        if element not in ['Geo', 'Anemo']:
            self.attached_element.append(element)
        return False

    """
    States and print
    """

    def reset(self):
        for skill in self.skills:
            skill.reset()

        self.health = self.health_limit
        self.energy = 0

        self.weapon = None
        self.artifact = None
        self.talent = False
        self.buffs = []
        
        self.attached_element = []
        self.active = False
        self.activate_cost = 1    
        self.alive = True


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
            
            'attached_element': self.attached_element,
            'active': self.active,
            'activate_cost': self.activate_cost,
            'alive': self.alive
        }
        
    def __repr__(self):
        return f"{self.name} | H: {self.health} / {self.health_limit} | E: {self.energy} / {self.energy_limit} {'| <*>'if self.active else ''}\n" + \
               f"Buffs: {''.join([buff.__repr__() for buff in self.buffs])}\n" + \
               f"T: {self.talent} {('W: ' + self.weapon.name) if self.weapon else ''} {('A: ' + self.artifact.name) if self.artifact else ''}\n" + \
               f"E: {self.element:<5} | {' '.join(self.attached_element)}"


class Cyno(Character):
    def __init__(self, name, pool):
        super().__init__(name, pool)

        pass       

character_cls = {
    'Cyno': Cyno
}

                
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
    
    # print('Available characters: ', chrs)
    
    return [character_cls[name](name, pool) if name in character_cls else Character(name, pool) for name in names]



    
        
if __name__ == '__main__':
    pool = load_js('Characters')
    print('Available Characters: ', len(pool))
    dump_js('test_character_list', [i['name'] for i in pool])


