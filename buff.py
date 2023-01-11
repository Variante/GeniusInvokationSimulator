class Buff:
    def __init__(self, source, code, char_ptr=None):
        self.source = source
        self.code = code
        self.life = 1
        self.init_life = self.life 
        self.rf_by_round = 1 # life reduced per round
        self.rf_by_activated = 1 # life reduced by activated
        self.attribs = {}
        self.condition = None
        self.char_ptr = char_ptr
        self._parse_code(code)

    # buff parse engine
    def _parse_code(self, code):
        if code.startswith('buff '):
            cmds = code[5:].split(',')
        else:
            cmds = code.split(',')
        for cmd in cmds:
            if len(cmd) == 0:
                continue
            cmdw = cmd.split()
            if cmdw[0] == 'life':
                self.life = int(cmdw[1])
                self.rf_by_round = int(cmdw[2])
                self.rf_by_activated = int(cmdw[3])
                self.init_life = self.life 
            elif cmdw[0] == 'when':
                self.condition = ' '.join(cmdw[1:])
            elif len(cmdw) > 2:
                self.attribs[cmdw[0]] = tuple(cmdw[1:-1] + [int(cmdw[-1])])
            elif len(cmdw) == 2:
                self.attribs[cmdw[0]] = int(cmdw[1])
            else:
                self.attribs[cmdw[0]] = 1
                
    def query(self, keyword):
        value = self.attribs.get(keyword, 0)
        if 'until_leave' in self.attribs:
            disabled = self.life > 0
        else:
            disabled =  self.life <= 0
        if self.condition is not None:
            disabled |= not eval(self.condition)
        if disabled:
            if isinstance(value, int):
                value = 0
            elif isinstance(value, tuple):
                value = (value[0], 0)
        return value

    def show_all_attr(self):
        return self.attribs.keys()

    def on_activated(self):
        self.life -= self.rf_by_activated
        
    def on_round_finished(self):
        if 'refresh' in self.attribs:
            self.life = self.init_life
        else:
            self.life -= self.rf_by_round

    def remove_keyword(self, kw):
        del self.attribs[kw]
        
    def change_keyword(self, kw, v):
        self.attribs[kw] = v

    def should_leave(self):
        return self.life <= 0 and 'stay' not in self.attribs
        
    def state(self):
        return {i:j for i, j in vars(self).items() if i not in ['condition', 'char_ptr', 'code']}

    def __repr__(self):
        if self.life == 0:
            return ''
        attribs = ','.join([f'{i}({self.attribs[i]})' for i in self.attribs])
        return f"[{attribs} from {self.source} ({self.life})]"


class Weapon(Buff):
    def __init__(self, card, code, char_ptr, weapon_type):
        # Put life in the front so that it can be overrided, and remove head "weapon"
        source = card.code_name
        super().__init__(source, 'life 1 0 1,' + code[7:], char_ptr)
        self.wtype = weapon_type
        self.name = source
        self.des = card.des

    # In weapon: use life as a counter, which means how many times we used the weapon
    # When the round finished, reset the life of the weapon
    def on_round_finished(self):
        self.life = self.init_life


class Artifact(Buff):
    def __init__(self, card, code, char_ptr):
        source = card.code_name
        # Put life in the front so that it can be overrided, and remove head "artifact"
        super().__init__(source, 'life 1 0 1,' + code[9:], char_ptr)
        self.name = source
        self.des = card.des

    # In weapon: use life as a counter, which means how many times we used the weapon
    # When the round finished, reset the life of the weapon
    def on_round_finished(self):
        self.life = self.init_life

    

class Summon(Buff):
    def __init__(self, source, data, talent):
        code = data['code']
        if talent:
            code = data.get('code_talent', code)
        super().__init__(source, code)
        self.name = data['name']
        self.code_name = data['code_name']
        self.attribs['on_round_finished'] = 1

    def heal(self, num):
        self.life += num

    def should_leave(self):
        return self.life <= 0
        
    def __repr__(self):
        if self.life == 0:
            return ''
        return f'{self.name}({self.life}): ' + ','.join([f'{i}({self.attribs[i]})' for i in self.attribs]) + \
            f" from {self.source}"


class ShieldSummon(Summon):
    def __init__(self, source, data, deck):
        super().__init__(source, data, False)

    def query(self, keyword):
        value = self.attribs.get(keyword, 0)
        if keyword == 'dmg_down':
            disabled = self.life <= 0
        else:
            disabled =  self.life > 0
        if disabled:
            if isinstance(value, int):
                value = 0
            elif isinstance(value, tuple):
                value = (value[0], 0)
        return value



class Melody_Loop(Summon):
    def __init__(self, source, data, deck): 
        for char in deck.characters:
            if char.code_name == 'barbara':
                break
        super().__init__(source, data, char.talent)
        self.char_ptr = char
        self.round_usage = 1

    def query(self, keyword):
        value = self.attribs.get(keyword, 0)
        if keyword == 'switch_cost_down':
            disabled = not (self.round_usage != 0 and self.char_ptr.alive() and self.char_ptr.talent)
        else:
            disabled = False
        if disabled:
            if isinstance(value, int):
                value = 0
            elif isinstance(value, tuple):
                value = (value[0], 0)
        return value

    def on_activated(self):
        self.round_usage = 0

    def on_round_finished(self):
        self.life -= 1
        self.round_usage = 1

class Support(Buff):
    def __init__(self, source, action):
        super().__init__(source, action.code[8:]) # remove support head
        self.name = action.name
        self.code_name = action.code_name
        # self.on_leave = action.on_leave
        
    def __repr__(self):
        return f'{self.name}({self.life}): ' + ','.join([f'{i}({self.attribs[i]})' for i in self.attribs]) + \
            f" from {self.source}"


    def on_round_finished(self, deck):
        if 'refresh' in self.attribs:
            # Similar to weapon, we use this life counter to describe the interal state
            # use in instead of query so that it will not be blocked
            self.life = self.init_life
        else:
            self.life -= self.rf_by_round

        # For Timaeus and Wagner
        for i in ['artifact_save', 'weapon_save']:
            if i in self.attribs:
                self.change_keyword(i, self.query(i) + 1)

    def state(self):
        res = super().state()
        display_val = None
        if 'until_leave' in self.attribs:
            display_val = self.init_life - self.life
        elif 'on_round_finished' in self.attribs or 'on_round_start' in self.attribs:
            display_val = self.life
        elif 'artifact_save' in self.attribs:
            display_val = self.attribs['artifact_save']
        elif 'weapon_save' in self.attribs:
            display_val = self.attribs['weapon_save']
        elif self.code_name == 'liu_su':
            display_val = self.round_life
        res['display_value'] = display_val
        return res

class Liben(Support):
    def __init__(self, source, action):
        assert action.code_name == 'liben'
        super().__init__(source, action) 
        
        self.collection = []

    def on_round_finished(self, deck):
        # collect dices
        for i, j in deck.current_dice.items():
            if j > 0 and i not in self.collection:
                deck.cost(i, 1)
                self.collection.append(i)

                if len(self.collection) >= 3:
                    break    
        self.life = self.init_life - len(self.collection)


class LiuSu(Support):
    def __init__(self, source, action):
        assert action.code_name == 'liu_su'
        super().__init__(source, action) 

        self.round_life = 2
    
    def on_round_finished(self, deck):
        self.life = 1
        self.round_life -= 1

    def should_leave(self):
        return self.round_life <= 0 

summon_cls = {
    'melody_loop': Melody_Loop,
    'reflection': ShieldSummon,
    'oceanic_mimic_frog': ShieldSummon,
}

support_cls = {
    'liben': Liben,
    'liu_su': LiuSu

}