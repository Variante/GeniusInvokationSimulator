from utils import *
from dices import Dices
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
        self.transfer_buff = []
            
        self.to_pull_actions = init_actions(deck['actions'])
        self.used_actions = []
        self.available_actions = []
        
        self.pre_pull_num = 2
        # self.alive = self._is_alive()
        self.current_dice = self.d.roll()
        self.agent = agent
        
        self.last_alive = [True] * len(self.characters)
        
        self.enemy_ptr = None
    
    def has_alive_changed(self):
        changed = False
        for i, c in enumerate(self.characters):
            if self.last_alive[i] ^ c.alive:
                self.last_alive[i] = c.alive
                changed = True
        return changed
        
    
    def is_alive(self):
        res = False
        for i in self.characters:
            res |= i.alive
        return res
    
    def shuffle(self):
        random.shuffle(self.to_pull_actions)
        
    def roll(self):
        self.current_dice = self.d.roll()
        
    def reroll(self, keep, total_num=8):
        self.current_dice = self.d.roll(total_num=total_num, keep=keep)
        
    def _pull(self, pull_num):
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
            self.current_dice[d_type] -= d_num
   
    def pull(self):
        return self._pull(self.pre_pull_num)
        
    def state(self):
        res = {
            'current_dice': self.current_dice,
            'characters': [i.state() for i in self.characters],
            'to_pull_actions': [i.state() for i in self.to_pull_actions],
            'used_actions': [i.state() for i in self.used_actions],
            'available_actions': [i.state() for i in self.available_actions],
        }
        return res
    
    def activate(self, code_name):
        # transfer buffs if necessary
        current_char = self.get_current_character()
        if current_char is not None:
            buffs = current_char.deactivate()
        self.get_character(code_name).activate()
    
    def get_current_element(self):
        for i in self.characters:
            if i.active:
                return i.element
                
    def get_current_character(self):
        for i in self.characters:
            if i.active:
                return i
    
    def get_enemy_current_character(self):
        for i in self.enemy_ptr.characters:
            if i.active:
                return i
    
    def get_character(self, code_name):
        for i in self.characters:
            if i.code_name == code_name:
                return i
    
    def get_action_space(self):
        char = self.get_current_character()
        # query character skill
        if char is not None:
            res = char.get_action_space(self)
        else:
            # switch character due to death (free switch)
            return [f"activate {i.code_name}" for i in self.characters if i.alive]
        
        # query action cards
        visited_action = set()
        for i in self.available_actions:
            if i.code_name not in visited_action:
                res.extend(i.get_action_space(self))
            visited_action.add(i.code_name)
        
        # query switch character
        for char in self.characters:
            if char.alive and not char.active:
                res.extend(
                generate_action_space(build_cost(char.activate_cost),
                self.current_dice, char, 
                prefix=f'activate {char.code_name}'))
        res.append('finish')
        return res
    
    def keep_action(self, keep_card):
        assert len(self.available_actions) == len(keep_card)
        for i in range(len(keep_card) - 1, -1, -1):
            if keep_card[i] == 0:
                self.to_pull_actions.append(self.available_actions.pop(i))
    
    def execute_action(self, code_name):
        for idx, i in enumerate(self.available_actions):
            if i.code_name == code_name:
                break
        action = self.available_actions.pop(idx)
        self.used_actions.append(action)
        return action
    
    def on_round_finished(self):
        for cha in self.characters:
            cha.on_round_finished()
    
    def __repr__(self):
        return json.dumps(self.state())
        
    def print_deck(self):
        print_dice(self.current_dice)
        print('-' * 40)
        print('Characters:')
        for c in self.characters:
            print(' ')
            print(c)
            
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
    d.pull()
    print('Current dices: ', d.current_dice, sep = "\n")
    print('Action space: ')
    print(*d.get_action_space(), sep = "\n")
    print('-' * 8)