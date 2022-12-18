from utils import *
from dices import Dices
from characters import init_characters
from actions import init_actions
import random

class Deck:
    def __init__(self, deck_name):
        self.d = Dices()
        deck = load_js(deck_name)
        self.characters = init_characters(deck['characters'])
        self.to_pull_actions = init_actions(deck['actions'])
        self.used_actions = []
        self.available_actions = []
        
        self.pre_pull_num = 2
        self.alive = self._is_alive()
        self.current_dice = self.d.roll()
    
    def _is_alive(self):
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
    
    def get_current_element(self):
        for i in self.characters:
            if i.active:
                return i.main_element
                
    def get_current_character(self):
        for i in self.characters:
            if i.active:
                return i
    
    def get_action_space(self):
        res = []
        for i in self.available_actions:
            res.extend(i.get_action_space(self))
        res.extend(self.get_current_character().get_action_space(self))
        res.append('finish turn')
        return res
    
    def __repr__(self):
        return json.dumps(self.state())
        

if __name__ == '__main__':
    d = Deck('p1')
    d.reroll(keep=[0, 0, 0, 0, 0, 3, 1, 1], total_num=5)
    print('Current dices: ', d.current_dice)
    print(d.get_action_space())
    print('-' * 8)