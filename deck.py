from utils import *
from dices import Dices
from buff import *
from characters import init_characters
from actions import init_actions, GenAction
import random

class Deck:
    def __init__(self, deck_name, agent):
        self.d = Dices()
        deck = load_js(deck_name)
        self.characters = init_characters(deck['characters'])
        for c in self.characters:
            c.deck_ptr = self
        self.characters[0].active = True
        self.to_pull_actions = init_actions(deck['actions'])
        self.used_actions = []
        self.available_actions = []
        
        self.current_dice = self.d.roll()
        self.agent = agent
        
        self.enemy_ptr = None
        self.game_ptr = None
        
        self.summon_pool = load_js('Summons')
        self.summons = []
        self.supports = []

        # team buff
        self.buffs = []
        
        self.defeated_this_round = 0
        self.deck_id = 0

    """
    Save, load, states and prints
    """
    def reset(self):
        for c in self.characters:
            c.reset()
        self.characters[0].active = True

        self.to_pull_actions = [i for i in self.to_pull_actions + self.used_actions + self.available_actions if 'generated' not in i.tags]
        self.used_actions = []
        self.available_actions = []
        self.current_dice = self.d.roll()

        self.summons = []
        self.supports = []
        # team buff
        self.buffs = []
        self.defeated_this_round = 0

    def save(self):
        res = self.state()
        res['defeated_this_round'] = self.defeated_this_round
        return res

    def state_for_enemy(self):
        return {
            'current_dice_num': count_total_dice(self.current_dice),
            'characters': [i.state() for i in self.characters],
            'summons': [i.state() for i in self.summons],
            'supports': [i.state() for i in self.supports],
            'buffs': [i.state() for i in self.buffs]
        }

    def state(self):
        res = self.state_for_enemy()
        res['current_dice'] = self.current_dice
        res['to_pull_actions'] = [i.state() for i in self.to_pull_actions]
        res['used_actions'] = [i.state() for i in self.used_actions]
        res['available_actions'] = [i.state() for i in self.available_actions]
        return res

    def __repr__(self):
        return json.dumps(self.state())
        
    def print_deck(self):
        print_dice(self.current_dice)
        print('-' * 40)
        print(f'Team buffs: {"".join([buff.__repr__() for buff in self.buffs])}')
        print('Characters: ')
        for c in self.characters:
            print(' ')
            print(c)
        print('-' * 40)
        print('Supports: ')
        for s in self.supports:
            print(s)
        print('-' * 40)
        print('Summons: ')
        for s in self.summons:
            print(s)
        print('-' * 40)
        print('Cards:')
        for a in self.available_actions:
            print(a)
        print('-' * 40)
         
    def print_actions(self):
        opt = []
        for i in self.get_action_space():
            s = '- ' + i.split(';')[0]
            if s not in opt:
                opt.append(s)
        print(*opt, sep='\n')

    def get_action_space(self):
        char = self.get_current_character()
        assert char.alive()

        res = char.get_action_space(self)
        # query action cards
        visited_action = set()
        for i in self.available_actions:
            if i.code_name not in visited_action:
                res.extend(i.get_action_space(self))
            visited_action.add(i.code_name)
        
        # query switch character, first calcualte action card
        c_mode = char.query_buff('switch_cost_down') + self.query_team_buff('switch_cost_down')
        
        for char in self.characters:
            if char.alive() and not char.active:
                sw_cost = max(char.activate_cost - c_mode, 0)
                res.extend(
                generate_action_space(build_cost(sw_cost),
                self.current_dice, char, 
                prefix=f'switch {char.code_name}'))
        res.append('finish')
        return res

    """
    Get status
    """
    def has_active_character(self):
        res = False
        for c in self.characters:
            res |= c.active
        if res:
            return True
        # print(f'[R{self.game_ptr.round_num:02d}-S{self.game_ptr.step_num:02d}] Player {self.deck_id + 1} needs to switch character')
        res = self.game_ptr.state()
        res['action_space'] = [f'activate {i.code_name}' for i in self.characters if i.alive()]
        """
        print(res['action_space'])
        print('-' * 10)
        """
        if len(res['action_space']) == 0:
            return False
        # ask user to activate a new character
        action = self.agent.get_action(res)
        self.game_ptr.action_history.append(f'Player {self.deck_id + 1}: {action}')
        self.get_character(action.split()[-1]).activate()
        return True

    def has_alive(self):
        res = False
        for c in self.characters:
            res |= c.alive()
        return res
    
    """
    Roll phase
    """
    def roll(self):
        keep = {}
        # an ugly way to process artifact effect and support
        for a in [c.artifact for c in self.get_alive_characters() if c.artifact is not None] + self.supports:
            for i in a.show_all_attr():
                if i.startswith('roll_'):
                    ele = i[5:]
                    if ele == 'current':
                        ele = self.get_current_character().element
                    keep[ele] = a.query(i) + keep.get(ele, 0)
        self.current_dice = self.d.roll(total_num=8, keep=keep)
        
    def reroll(self):
        # self.current_dice = self.d.roll(keep = np.array([0, 0, 0, 0, 0, 0, 0, 8]))
        keep = self.agent.get_keep_dice({'my_state': self.state()})
        self.current_dice = self.d.roll(total_num=count_total_dice(self.current_dice), keep=keep)

    def gen(self, d_type, d_num):
        gen_num = min(16 - count_total_dice(self.current_dice), d_num)
        if d_type == 'Rand':
            for _ in range(gen_num):
                d_type = self.d.random_type()
                self.cost(d_type, -1)
            return
        elif d_type == 'Current':
            d_type = self.get_current_element()
        # the max num of dices is 16
        self.cost(d_type, -gen_num)

    def cost(self, d_type, d_num):
        if d_type == 'energy':
            self.get_current_character().energy -= d_num
        else:
            
            try:
                self.current_dice[d_type] -= d_num
            except KeyError:
                # add dice
                self.current_dice[d_type] = -d_num
        
    """
    Draw card phase
    """
    def shuffle(self):
        random.shuffle(self.to_pull_actions)

    def _pull_card(self, action):
        # current actions are full
        if len(self.available_actions) >= 10:
            self.used_actions.append(action)
        else:
            self.available_actions.append(action)

    def pull_food(self, pull_num):
        c = 0
        for i, j in enumerate(self.to_pull_actions):
            if 'food'in j.tags:
                action = self.to_pull_actions.pop(i)
                self._pull_card(action)
                c += 1
                if c == pull_num:
                    break
                
    def pull(self, pull_num):
        for _ in range(pull_num):
            try:
                action = self.to_pull_actions.pop()
            except IndexError:
                return
            self._pull_card(action)

    def swap_card(self):
        keep_card = self.agent.get_keep_card({'my_state': self.state()})
        assert len(self.available_actions) == len(keep_card)
        c = 0
        for i in range(len(keep_card) - 1, -1, -1):
            if keep_card[i] == 0:
                self.to_pull_actions.append(self.available_actions.pop(i))
                c += 1
        self.pull(c)

    def use_card(self, code_name):
        for i in self.available_actions:
            if i.code_name == code_name:
                return i

    def drop_card(self, action):
        if action is None:
            return
        try:
            self.available_actions.remove(action)
            self.used_actions.append(action)
        except:
            pass

    def gen_card(self, code_name):
        action = GenAction(code_name)
        self._pull_card(action)

    def has_card_in_hand(self, code_name):
        for i in self.available_actions:
            if i.code_name == code_name:
                return True
        return False
        
    """
    Summons
    """
    def _proc_buffs(self, list_ptr, kw):
        i = 0
        while True:
            try:
                s = list_ptr[i]
                if s.query(kw):
                    buff_engine(s, self, self.enemy_ptr)
                if s.should_leave():
                    list_ptr.pop(i)
                    continue                    
                i += 1
            except IndexError:
                break

    def add_summon(self, source, code_name, talent=False):
        # fetch summon profile
        for i in self.summon_pool:
            if i['code_name'] == code_name:
                summon_data = i
                break
        
        # check existing summons
        if code_name in summon_cls:
            sobj = summon_cls[code_name](source, summon_data, self)
        else:
            sobj = Summon(source, summon_data, talent)
        for i, s in enumerate(self.summons):
            if s.code_name == code_name:
                self.summons[i] = sobj
                return
        
        # if we have too many summons
        if len(self.summons) >= 4:
            s = self.game_ptr.state()
            s['action_space'] = [f'replace {i.code_name}' for i in self.summons ]
            rep = self.agent.get_action(s)
            self.summons[s['action_space'].index(rep)] = sobj
        else:
            self.summons.append(sobj)

    def add_rand_summon(self, source, num, code_names):
        np.random.shuffle(code_names)
        for code_name in code_names[:num]:
            self.add_summon(source, code_name)

    def kill_summon(self, code_name):
        for s in self.summons:
            if s.code_name == code_name:
                self.summons.remove(s)
                return
    
    def kill_all_summons(self):
        self.summons = []

    def get_summon_buff(self, keyword):
        return [i for i in self.summons if i.query(keyword)]

    def proc_summon_buffs(self, kw):
        self._proc_buffs(self.summons, kw)


    """
    Supports
    """
    def add_support(self, action, idx):
        # special support unit
        if "self-class" in action.tags:
            s = support_cls[action.code_name](action.code_name, action)
        else:
            s = Support(action.code_name, action)

        if len(self.supports) <= idx:
            self.supports.append(s)
        else:
            self.supports[idx] = s

        # activate location cost saving (trigger the counter)
        if 'location' in action.tags:
            # TODO not sure about this
            self.proc_support_buffs('location_save')

            """
            kw = 'location_save'
            cost = action.cost['d_num'][0]
            for s in self.supports:
                res = s.query(kw)
                if cost > 0:
                    s.on_activated()
                    cost -= res
                else:
                    break
            """
                
    def query_team_buff(self, keyword):
        val = 0
        for i in self.buffs + self.supports + self.summons:
            val += i.query(keyword)
        return val

    def take_team_buff(self, keyword):
        val = 0
        for i in self.buffs + self.supports + self.summons:
            res = i.query(keyword)
            if res > 0:
                val += res
                i.on_activated()
        return val

    def proc_support_buffs(self, kw):
        self._proc_buffs(self.supports, kw)

    def activate_support_buffs(self, code_name):
        for s in self.supports:
            if s.code_name == code_name:
                s.on_activated()

    """
    Modify characters
    """
    def transfer_equip(self, eq, src, dst):
        s = self.get_character(src)
        d = self.get_character(dst)

        if eq == 'artifact':
            s.artifact = d.artifact
            d.artifact = None
        elif eq == 'weapon':
            s.weapon = d.weapon
            d.weapon = None

    def recharge(self, cmdw):
        if cmdw[1] == 'any':
            for c in [self.get_current_character()] + self.get_bg_characters():
                if c.get_energy_need() > 0:
                    return c.recharge(int(cmdw[2]))
        elif cmdw[1] == 'Electro':
            for c in [self.get_current_character()] + self.get_bg_characters():
                if c.get_energy_need() > 0 and c.element == 'Electro':
                    return c.recharge(int(cmdw[2]))
        elif cmdw[1] == 'active':
            return self.get_current_character().recharge(int(cmdw[2]))
        elif cmdw[1] == 'to_active':
            cur = self.get_current_character()
            v = int(cmdw[2])
            for c in self.get_bg_characters():
                if cur.get_energy_need() > 0 and c.energy >= v:
                    cur.recharge(v)
                    c.recharge(-v)
            return True
        return False

    """
    Switch characters
    """
    def switch(self, code_name):
        cur = self.get_current_character()
        if cur is not None:
            if code_name == cur.code_name:
                return
            if cur.alive():
                cur.deactivate()
        self.get_character(code_name).activate()      
        # Liu Su
        self.proc_support_buffs('on_switch_finished')

    def switch_next(self, reversed=False):
        idx = self.get_current_character_idx()
        if idx is None:
            # no one is alive
            return
        l = len(self.characters)
        for i in range(1, l + l):
            c = self.characters[(idx + (i if reversed else -i)) % l]
            if c.alive():
                self.switch(c.code_name)
                return

    """
    Methods to fetch information
    """
    def count_character_by_faction(self, s):
        res = 0
        for c in self.get_alive_characters():
            if to_code_name(c.faction) == s:
                res += 1
        return res

    def get_current_element(self):
        return self.get_current_character().element

    def get_alive_characters(self):
        return [c for c in self.characters if c.alive()]
                
    def get_current_character(self):
        self.has_active_character()
        for c in self.characters:
            if c.active:
                return c
        

    def get_current_character_idx(self):
        self.has_active_character()
        for i, c in enumerate(self.characters):
            if c.active:
                return i
        
    def get_bg_characters(self):
        return [c for c in self.characters if c.alive() and not c.active]
    
    def get_enemy_current_character(self):
        return self.enemy_ptr.get_current_character()
    
    def get_character(self, code_name):
        for i in self.characters:
            if i.code_name == code_name:
                return i
    
    def get_character_idx(self, code_name):
        for idx, i in enumerate(self.characters):
            if i.code_name == code_name:
                return idx

    def get_summon(self, code_name):
        for i in self.summons:
            if i.code_name == code_name:
                return i

    """
    Round events
    """

    def on_round_start(self):
        # draw 2 cards
        self.pull(2)
        
        # get dices
        self.roll()
        self.reroll()
        for _ in range(self.query_team_buff('reroll')):
            self.reroll()

        # process support
        self.proc_support_buffs('on_round_start')
            
        # clear counter
        self.defeated_this_round = 0

    def on_round_finished(self):
        if not self.has_active_character():
            return 

        for cha in self.characters:
            cha.on_round_finished()
        
        for s in self.summons:
            s.on_round_finished()
            # this actually does nothing, we rely on on_activated, except melody_loop
        # process summons
        self.proc_summon_buffs('on_round_finished')

        for s in self.supports:
            s.on_round_finished(self)
        # process support
        self.proc_support_buffs('on_round_finished')
