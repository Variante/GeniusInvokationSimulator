class Buff:
    def __init__(self, source, code, char_ptr=None):
        self.source = source
        self.code = code
        self.life = 1
        self.init_life = self.life 
        self.rf_by_round = 1 # life reduced per round
        self.rf_by_activated = 1 # life reduced by activated
        self.attribs = {}
        self._parse_code(code)
        self.condition = None
        self.char_ptr = char_ptr

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
                self.condition = cmd[5:]
            elif len(cmdw) > 2:
                self.attribs[cmdw[0]] = tuple(cmdw[1:-1] + [int(cmdw[-1])])
            elif len(cmdw) == 2:
                self.attribs[cmdw[0]] = int(cmdw[1])
            else:
                if cmd.startswith('collect'):
                    self.attribs[cmdw[0]] = {}
                else:
                    self.attribs[cmdw[0]] = 1
                
    def query(self, keyword):
        value = self.attribs.get(keyword, 0)
        disabled = self.life <= 0
        disabled |= 'starts_since_next_round' in self.attribs and self.life == self.init_life
        disabled |= 'until_leave' in self.attribs and self.life <= 0
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
        self.life -= self.rf_by_round

    def remove_keyword(self, kw):
        del self.attribs[kw]
        
    def change_keyword(self, kw, v):
        self.attribs[kw] = v

    def state(self):
        return {i:j for i, j in vars(self).items() if i not in ['condition', 'char_ptr']}

    def __repr__(self):
        if self.life == 0:
            return ''
        attribs = ','.join([f'{i}({self.attribs[i]})' for i in self.attribs])
        return f"[{attribs} from {self.source} ({self.life})]"


class Weapon(Buff):
    def __init__(self, source, code, char_ptr, weapon_type):
        # Put life in the front so that it can be overrided, and remove head "weapon"
        super(Weapon, self).__init__(source, 'life 1 0 1,' + code[7:], char_ptr)
        self.wtype = weapon_type
        self.name = source

    # In weapon: use life as a counter, which means how many times we used the weapon
    # When the round finished, reset the life of the weapon
    def on_round_finished(self):
        self.life = self.init_life


class Artifact(Buff):
    def __init__(self, source, code, char_ptr):
        # Put life in the front so that it can be overrided, and remove head "artifact"
        super(Artifact, self).__init__(source, 'life 1 0 1,' + code[9:], char_ptr)
        self.name = source

    # In weapon: use life as a counter, which means how many times we used the weapon
    # When the round finished, reset the life of the weapon
    def on_round_finished(self):
        self.life = self.init_life

    

class Summon(Buff):
    def __init__(self, source, data):
        super(Summon, self).__init__(source, data['code'])
        self.name = data['name']
        self.code_name = data['code_name']

    def heal(self, num):
        self.life += num
        
    def __repr__(self):
        if self.life == 0:
            return ''
        return f'{self.name}: ' + ','.join([f'{i}({self.attribs[i]})' for i in self.attribs]) + \
            f" from {self.source} ({self.life})"

class Support(Buff):
    def __init__(self, source, action):
        super(Support, self).__init__(source, action.code)
        self.name = action.name
        self.code_name = action.code_name
        # self.on_leave = action.on_leave
        
    def __repr__(self):
        return f'{self.name}: ' + ','.join([f'{i}({self.attribs[i]})' for i in self.attribs]) + \
            f" from {self.source} ({self.life})"

    def on_round_finished(self):
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

    def should_leave(self):
        # For Liu Su
        if 'renew' in self.attribs and self.life == 0:
            self.life = self.init_life
            self.attribs['renew'] -= 1
            if self.attribs['renew'] < 1:
                del self.attribs['renew']

        # for liben, when activated by on_round_start, life should go to -1, and it will override the stay tag
        return (self.life == 0 and self.query('stay') == 0) or self.life < 0
