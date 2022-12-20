class Buff:
    def __init__(self, source, code):
        self.source = source
        self.code = code
        self.life = 1
        self.init_life = self.life 
        self.rf_by_round = 1 # life reduced per round
        self.rf_by_activated = 1 # life reduced by activated
        self.attribs = {}
        self._parse_code(code)

    # buff parse engine
    def _parse_code(self, code):
        if code.startswith('buff '):
            cmds = code[5:].split(',')
        else:
            cmds = code.split(',')
        for cmd in cmds:
            cmdw = cmd.split()
            if cmdw[0] == 'life':
                self.life = int(cmdw[1])
                self.rf_by_round = int(cmdw[2])
                self.rf_by_activated = int(cmdw[3])
                self.init_life = self.life 
            elif len(cmdw) > 2:
                self.attribs[cmdw[0]] = tuple(cmdw[1:-1] + [int(cmdw[-1])])
            elif len(cmdw) == 2:
                self.attribs[cmdw[0]] = int(cmdw[1])
            else:
                self.attribs[cmdw[0]] = 1
                
    def query(self, keyword):
        value = self.attribs.get(keyword, 0)
        if ('starts_since_next_round' in self.attribs and self.life == self.init_life) or self.life <= 0:
            if isinstance(value, int):
                value = 0
            elif isinstance(value, tuple):
                value = (value[0], 0)
        return value

    def on_activated(self):
        self.life -= self.rf_by_activated
        
    def on_round_finished(self):
        self.life -= self.rf_by_round

    def state(self):
        return vars(self)

    def __repr__(self):
        attribs = ','.join([f'{i}({self.attribs[i]})' for i in self.attribs])
        return f"[{attribs} from {self.source} ({self.life})]"


class Summon(Buff):
    def __init__(self, source, data):
        super(Summon, self).__init__(source, data['code']+',on_round_finished')
        self.name = data['name']
        self.code_name = data['code_name']
        
    def remove_keyword(self, kw):
        del self.attribs[kw]
        
    def change_keyword(self, kw, v):
        self.attribs[kw] = v
        
    def __repr__(self):
        return f'{self.name}: ' + ','.join([f'{i}({self.attribs[i]})' for i in self.attribs]) + \
            f" from {self.source} ({self.life})"

class Support(Buff):
    def __init__(self, source, data):
        super(Support, self).__init__(source, data['code'])
        self.name = data['name']
        self.code_name = data['code_name']
        
    def __repr__(self):
        return f'{self.name}: ' + ','.join([f'{i}({self.attribs[i]})' for i in self.attribs]) + \
            f" from {self.source} ({self.life})"