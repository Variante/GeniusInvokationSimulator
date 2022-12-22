from utils import *
from dices import Dices
from buff import Summon, Support
from characters import init_characters
from actions import init_actions
import random

class Deck:
    def __init__(self, deck_name, agent):
        self.d = Dices()
        deck = load_js(deck_name)
        self.characters = init_characters(deck['characters'])
        for c in self.characters:
            c.deck_ptr = self
        self.character_order = list(range(len(self.characters)))
        self.transfer_buff = []
            
        self.to_pull_actions = init_actions(deck['actions'])
        self.used_actions = []
        self.available_actions = []
        
        # self.alive = self._is_alive()
        self.current_dice = self.d.roll()
        self.agent = agent
        
        self.last_alive = [True] * len(self.characters)
        
        self.enemy_ptr = None
        self.game_ptr = None
        
        self.summon_pool = load_js('Summons')
        self.summons = []
        self.supports = []
        
        self.defeated_this_round = 0
        self.deck_id = 0

    def save(self):
        res = self.state()
        res['last_alive'] = self.last_alive
        res['defeated_this_round'] = self.defeated_this_round
        return res
    
    def has_alive_changed(self):
        changed = False
        for i in self.character_order:
            c = self.characters[i].alive
            if self.last_alive[i] ^ c:
                self.last_alive[i] = c
                changed = True
        return changed
        
    
    def is_alive(self):
        res = False
        for i in self.character_order:
            res |= self.characters[i].alive
        return res
    
    def shuffle(self):
        random.shuffle(self.to_pull_actions)
        
    def roll(self):
        keep = {}
        # an ugly way to process artifact effect and support
        for a in [c.artifact for c in self.get_alive_characters() if c.artifact is not None] + self.supports:
            for i in a.show_all_attr():
                if i.startswith('roll_'):
                    ele = i[5:]
                    if ele == 'current_die':
                        ele = self.get_current_character().element
                    keep[ele] = a.query(i)
        self.current_dice = self.d.roll(keep=keep)
        
    def reroll(self, total_num=8):
        # self.current_dice = self.d.roll(keep = np.array([0, 0, 0, 0, 0, 0, 0, 8]))
        keep = self.agent.get_keep_dice(self.state())
        self.current_dice = self.d.roll(total_num=total_num, keep=keep)
        
    def pull_one_food(self):
        for i, j in enumerate(self.to_pull_actions):
            if 'food'in j.tags:
                action = self.to_pull_actions.pop(i)
                # current actions are full
                if len(self.available_actions) >= 10:
                    self.used_actions.append(action)
                else:
                    self.available_actions.append(action)


    def pull(self, pull_num):
        for _ in range(pull_num):
            try:
                action = self.to_pull_actions.pop()
            except IndexError:
                return
            # current actions are full
            if len(self.available_actions) >= 10:
                self.used_actions.append(action)
            else:
                self.available_actions.append(action)
   
    def cost(self, d_type, d_num):
        if d_type == 'energy':
            self.get_current_character().energy -= d_num
        else:
            try:
                self.current_dice[d_type] -= d_num
            except KeyError:
                # add dice
                self.current_dice[d_type] = -d_num

   
    def pre_round_pull(self):
        pre_pull_num = 2
        return self.pull(pre_pull_num)
        

    def state_for_enemy(self):
        return {
            'current_dice_num': count_total_dice(self.current_dice),
            'characters': [i.state() for i in self.characters],
            'summons': [i.state() for i in self.summons],
            'supports': [i.state() for i in self.supports]
        }
        

    def state(self):
        res = self.state_for_enemy()
        res['current_dice'] = self.current_dice
        res['to_pull_actions'] = [i.state() for i in self.to_pull_actions]
        res['used_actions'] = [i.state() for i in self.used_actions]
        res['available_actions'] = [i.state() for i in self.available_actions]
        res['action_space'] = self.get_action_space()
        return res

    def add_summon(self, source, code_name):
        for i in self.summon_pool:
            if i['code_name'] == code_name:
                summon_data = i
                break
        
        sobj = Summon(source, summon_data)
        for i, s in enumerate(self.summons):
            if s.code_name == code_name:
                self.summons[i] = sobj
                return
                
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
                s.kill()
                self.summons.remove(s)
                return
    
    def kill_all_summons(self):
        self.summons = []

    def transfer_equip(self, eq, src, dst):
        s = self.get_character(src)
        d = self.get_character(dst)

        if eq == 'artifact':
            s.artifact = d.artifact
            d.artifact = None
        elif eq == 'weapon':
            s.weapon = d.weapon
            d.weapon = None

    def get_summon_buff(self, keyword):
        return [i for i in self.summons if i.query(keyword)]
        
    def add_support(self, action, idx):
        s = Support(action.code_name, action)
        if len(self.supports) >= idx:
            self.supports.append(s)
        else:
            self.supports[idx] = s

        # special code for nre:
        if s.code_name == 'nre':
            self.pull_one_food()

        # activate location cost saving (trigger the counter)
        if 'location' in action.tags:
            kw = 'location_save'
            cost = action.cost['d_num'][0]
            for s in self.supports:
                res = s.query(kw)
                if cost > 0:
                    s.on_activated()
                    cost -= res
                else:
                    break
         
    def _deactivate(self):
        # transfer buffs if necessary
        current_char = self.get_current_character()
        idx = self.character_order.pop(0)
        if current_char.alive:
            # manually deactivate
            buffs = current_char.deactivate()
            # add back to the end
            self.character_order.append(idx)
        # print('[_deactivate]', idx, self.character_order)

    def _activate(self, idx):
        # when actively switch the character
        if self.game_ptr.current_agent == self.deck_id:
            self.take_support_buff('switch_cost_down')
        
        self.character_order.remove(idx)
        self.character_order.insert(0, idx)
        self.characters[idx].activate()

        self.proc_support_buffs('on_switch_finished')



    def activate_by_id(self, idx):
        self._deactivate()
        # move to the first
        # print('[activate_by_id]', idx, self.character_order)
        if idx not in self.character_order:
            # character killed by skill first, then request a switch
            # in this case just ignore the switch
            """
            print('\n' * 5)
            print(self.characters[idx])
            print('Killed')
            print('\n' * 5)
            """
            return
        self._activate(idx)
            
    def activate(self, code_name):
        self._deactivate()
        idx = self.get_character_idx(code_name)
        if idx not in self.character_order:
            return
        self._activate(idx)

    def activate_prev(self):
        try:
            idx = self.character_order[-1]
        except IndexError:
            return
        self.activate_by_id(idx)
    
    def activate_next(self):
        try:
            idx = self.character_order[1]
        except IndexError:
            return
        self.activate_by_id(idx)

    def count_character_by_faction(self, s):
        res = 0
        for c in self.get_alive_characters():
            if to_code_name(c.faction) == s:
                res += 1
        return res

    def get_current_element(self):
        return self.get_current_character().element

    def get_alive_characters(self):
        return [self.characters[i] for i in self.character_order]
                
    def get_current_character(self):
        return self.characters[self.character_order[0]]
        
    def get_other_characters(self):
        try:
            return [self.characters[i] for i in self.character_order[1:]]
        except IndexError:
            return []
    
    def get_enemy_current_character(self):
        return self.enemy_ptr.characters[self.enemy_ptr.character_order[0]]
    
    def get_character(self, code_name):
        for i in self.characters:
            if i.code_name == code_name:
                return i

    def get_summon(self, code_name):
        for i in self.summons:
            if i.code_name == code_name:
                return i
    
    def get_character_idx(self, code_name):
        for idx, i in enumerate(self.characters):
            if i.code_name == code_name:
                return idx
    
    def get_action_space(self):
        char = self.get_current_character()
        # query character skill
        if char.alive:
            res = char.get_action_space(self)
        else:
            # activate character due to death (free switch)
            return [f"activate {i.code_name}" for i in self.characters if i.alive]
        
        # query action cards
        visited_action = set()
        for i in self.available_actions:
            if i.code_name not in visited_action:
                res.extend(i.get_action_space(self))
            visited_action.add(i.code_name)
        
        # query switch character, first calcualte action card
        c_mode = char.query_buff('switch_cost_down') + self.query_support_buff('switch_cost_down')
        
        for char in self.characters:
            if char.alive and not char.active:
                sw_cost = max(char.activate_cost - c_mode, 0)
                res.extend(
                generate_action_space(build_cost(sw_cost),
                self.current_dice, char, 
                prefix=f'switch {char.code_name}'))
        res.append('finish')
        return res
    
    def keep_action(self, keep_card):
        assert len(self.available_actions) == len(keep_card)
        c = 0
        for i in range(len(keep_card) - 1, -1, -1):
            if keep_card[i] == 0:
                self.to_pull_actions.append(self.available_actions.pop(i))
                c += 1
        self.pull(c)
    
    def use_action_card(self, code_name):
        for idx, i in enumerate(self.available_actions):
            if i.code_name == code_name:
                break
        action = self.available_actions.pop(idx)
        self.used_actions.append(action)
        return action
    
    def query_support_buff(self, keyword):
        val = 0
        for i in self.supports:
            val += i.query(keyword)
        return val

    def take_support_buff(self, keyword):
        val = 0
        for i in self.supports:
            res = i.query(keyword)
            if res > 0:
                val += res
                i.on_activated()
        return val

    def proc_support_buffs(self, kw):
        i = 0
        while True:
            try:
                s = self.supports[i]
                if s.query(kw):
                    # check the effect of this summon (buff)
                    # thanks paimon
                    self.get_current_character()._engine_buff(s)
                if s.should_leave():
                    self.supports.pop(i)
                else:
                    i += 1
            except IndexError:
                break
    
    def refresh_summons(self):
        self.summons = [i for i in self.summons if i.life > 0]

    def on_round_start(self):
        # draw 2 cards
        self.pre_round_pull()
        
        # get dices
        self.roll()
        self.reroll()
        for _ in range(self.query_support_buff('query_support_buff')):
            self.reroll()

        # process support
        self.proc_support_buffs('on_round_start')
            
        # clear counter
        self.defeated_this_round = 0

    def on_round_finished(self):
        for cha in self.characters:
            cha.on_round_finished()
            
        # process summons
        i = 0
        while True:
            try:
                s = self.summons[i]
                # check the effect of this summon (buff)
                self.get_current_character()._engine_buff(s)
                s.on_round_finished()
                if s.life > 0:
                    i += 1
                else:
                    self.summons.pop(i)
            except IndexError:
                break

        # process support
        i = 0
        while True:
            try:
                s = self.supports[i]
                if s.query('on_round_finished'):
                    # check the effect of this summon (buff)
                    self.get_current_character()._engine_buff(s)
                s.on_round_finished()

                if 'collect_liben' in s.attribs:
                    st = s.attribs['collect_liben']
                    for k, j in self.current_dice.items():
                        if j > 0:
                            st[k] = 1
                    s.life = max(s.init_life - len(st), 0)

                if s.should_leave():
                    self.supports.pop(i)
                else:
                    i += 1
            except IndexError:
                break

    def recharge(self, cmdw):
        if cmdw[1] == 'any':
            for i in self.character_order:
                c = self.characters[i]
                if c.get_energy_need() > 0:
                    c.recharge(int(cmdw[2]))
                    return True
            return False
        elif cmdw[1] == 'active':
            self.get_current_character().recharge(int(cmdw[2]))
            return True
        elif cmdw[1] == 'to_active':
            cur = self.get_current_character()
            v = int(cmdw[2])
            for i in self.character_order[1:]:
                c = self.characters[i]
                if cur.get_energy_need() > 0 and c.energy >= v:
                    cur.recharge(v)
                    c.recharge(-v)
            return True
                
    def __repr__(self):
        return json.dumps(self.state())
        
    def print_deck(self):
        print_dice(self.current_dice)
        print('-' * 40)
        print('Characters: ', self.character_order)
        for c in self.characters:
            print(' ')
            print(c)
        print('-' * 40)
        print('Supports: ')
        for s in self.supports:
            print(' ')
            print(s)
        print('-' * 40)
        print('Summons: ')
        for s in self.summons:
            print(' ')
            print(s)
        print('-' * 40)
        print('Cards:')
        for a in self.available_actions:
            print(a)
        print('-' * 40)
         
    def print_actions(self):
        print(*['- ' + i for i in self.get_action_space()], sep='\n')
        
        
if __name__ == '__main__':
    d = Deck('p1', None)
    d.reroll(keep=[0, 2, 0, 0, 0, 0, 0, 0], total_num=2)
    d.pre_round_pull()
    print('Current dices: ', d.current_dice, sep = "\n")
    print('Action space: ')
    print(*d.get_action_space(), sep = "\n")
    print('-' * 8)
    print(d)
    