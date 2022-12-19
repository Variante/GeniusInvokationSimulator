from utils import *
from deck import Deck
from agent import Agent
import random

class Game:
    def __init__(self, decks):
        assert len(decks) == 2
        self.decks = decks
        self.agents = [i.agent for i in decks]
        for i in range(2):
            self.agents[i].enemy_ptr = self.agents[1 - i]
        
        self.agent_num = len(decks)
        self.round_num = 0
        self.agent_moves_first = None
        self.current_agent = 0
        self.finish_round = [False] * self.agent_num
        
        self.switch_agent = False
        
    def next_agent(self):
        idx = self.current_agent
        while True:
            idx += 1
            idx %= self.agent_num
            # print(idx, self.finish_round)
            if not self.finish_round[idx]:
                break
        self.current_agent = idx
        
    def is_round_finished(self):
        res = True
        for i in self.finish_round:
            res &= i
        return res
        
    def check_win(self):
        res = [i.is_alive() for i in self.decks]
        if res[0] and res[1]:
            # ongoing
            return -1
        elif res[0] and not res[1]:
            return 1
        else:
            return 2
            
                
    def state(self):
        return {
                'my_state': self.get_current_deck().state(),
                'other_state': self.get_other_deck().state(),
                'action_space': self.get_current_deck().get_action_space()
            }
            
    def get_current_deck(self):
        return self.decks[self.current_agent]
        
    def get_other_deck(self):
        for i, j in enumerate(self.decks):
            if i != self.current_agent:
                return j
        
        
    def engine_action(self, action, target):
        code_name = action.code_name
        target = self.get_current_deck().get_character(target)
        cmds = action.code.split(';')
        for cmd in cmds:
            cmdw = cmd.split()
            if cmdw[0] == 'heal':
                target.heal(int(cmdw[1]))
            elif cmdw[0] == 'buff':
                target.add_buff(action.code_name, cmd)
            else:
                raise NotImplementedError(f'[engine_action]{cmd}')
            
    def parse_space_action(self, action):
        if action == 'finish':
            self.finish_round[self.current_agent] = True
            # player who finishes first moves first in the next round
            if self.agent_moves_first is None:
                self.agent_moves_first = self.current_agent
            self.switch_agent = True
            return    
        cmds = action.split(';')
        for cmd in cmds:
            cmdw = cmd.split()
            if cmdw[0] == 'action':
                action = self.get_current_deck().execute_action(cmdw[1])
                self.engine_action(action, cmdw[2])
            elif cmdw[0] == 'convert':
                action = self.get_current_deck().execute_action(cmdw[1])
            elif cmdw[0] == 'skill':
                my_char = self.get_current_deck().get_character(cmdw[1])
                enemy_char = self.get_other_deck().get_current_character()
                my_char.get_skill(cmdw[2]).exec(self, my_char, enemy_char)
                self.switch_agent = True
            elif cmdw[0] == 'cost':
                d_num = int(cmdw[1])
                self.get_current_deck().cost(cmdw[2], d_num)
            elif cmdw[0] == 'gen':
                d_num = int(cmdw[1])
                d_type = cmdw[2]
                if d_type == 'Rand':
                    d_type = self.get_current_deck().d.random_type()
                self.get_current_deck().cost(d_type, -d_num)
            elif cmdw[0] == 'activate':
                self.get_current_deck().activate(cmdw[1])
                self.switch_agent = True
            else:
                raise NotImplementedError(f'[parse_space_action]{cmd}')
                
   
    def on_round_finished(self):
        # update all states
        for deck in self.decks:
            deck.on_round_finished()
        
        # check if character dead
        self.has_alive_changed()
        self.current_agent = self.agent_moves_first
        self.agent_moves_first = None
        
            
    def print_desk(self, event=''):
        print('\n' * 3 + '=' * 50)
        print(f"[Round {self.round_num:02d}] {event}")
        print('-' * 50)
        for i, d in enumerate(self.decks):
            print(f'Player {i + 1} ' + ('[√]' if self.finish_round[i] else '[ ]') + (' <*>' if self.current_agent == i else ''))
            d.print_deck()
            if self.current_agent == i:
                print('Available actions:')
                d.print_actions()
            print('-' * 50)
   
    def has_alive_changed(self):
        for i, d in enumerate(self.decks):
            if d.has_alive_changed():
                tmp = self.current_agent
                self.current_agent = i
                assert i != tmp
                print(f'\n\nPlayer {i + 1} needs to switch character')
                d.print_actions()
                # ask user to activate a new character
                agent = self.agents[self.current_agent]
                action = agent.get_action(self.state())
                self.parse_space_action(action)
                self.switch_agent = True
                self.current_agent = tmp
                return
            
    
    def game_loop(self, show=False):
        for i in self.decks:
            i.shuffle()
            i._pull(5)
            # swap init cards
            if show:
                self.print_desk(f'Player {self.current_agent + 1} init cards')
            keep_card = i.agent.get_keep_card(self.state())
            i.keep_action(keep_card)
            if show:
                self.print_desk(f'Player {self.current_agent + 1} swap cards ' + ','.join([str(i) for i in keep_card]))
            
        # round start
        while self.check_win() < 0 and self.round_num < 5:
            # start a new round
            self.round_num += 1
            self.finish_round = [False] * self.agent_num
            
            # pull cards
            for i in self.decks:
                i.pull()
            
            if show:
                self.print_desk('Pull cards')
            # throw dices
            for d in self.decks:
                d.roll()
                keep_dice = d.agent.get_keep_dice(self.state())
                d.reroll(keep=keep_dice)
                
            while True:
                self.switch_agent = False
                
                tmp = self.current_agent
                agent = self.agents[self.current_agent]
                action = agent.get_action(self.state())
                self.parse_space_action(action)
                
                ret = self.check_win()
                if ret >= 0:
                    if show:
                        self.print_desk(f'Player {tmp + 1} exec: ' + action)
                    return ret
                    
                self.has_alive_changed()
                if self.is_round_finished():
                    break
                if self.switch_agent:
                    self.next_agent()
                    
                if show:
                    self.print_desk(f'Player {tmp + 1} exec: ' + action)
                
                
            # one round finished
            self.on_round_finished()
            if show:
                self.print_desk('round finished')
            
        return self.check_win()
        
        
    def print_winner(self, ret):
        print('\n' * 3 + '=' * 20)
        if ret > 0:
            print(f'Game finished. The winner is Player {ret}')
        else:
            print('Game finished. It is a draw')
        print('=' * 20)
        
        
if __name__ == '__main__':
    g = Game([Deck('p1', Agent()), Deck('p1', Agent())])
    ret = g.game_loop(show=True)
    g.print_winner(ret)
    