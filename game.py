from utils import *
from deck import Deck
from agent import Agent
import random

class Game:
    def __init__(self, decks, agents):
        self.decks = decks
        self.agents = agents
        assert len(self.decks) == len(self.agents)
        
        self.agent_num = len(agents)
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
        res = True
        for i in self.decks:
            res &= i.alive
        if res:
            return -1 # on going game
            
        res = False
        for i in self.decks:
            res |= i.alive
        if not res:
            return 0 # Draw
            
        for i, j in enumerate(self.decks):
            if j.alive:
                return i + 1
                
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
                print(target)
                target.heal(int(cmdw[1]))
            elif cmdw[0] == 'feed':
                target.hungry = False
            else:
                print(f'Not implemented cmd {cmd}')
            
    def parse_action(self, action):
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
            elif cmdw[0] == 'cost':
                d_num = int(cmdw[1])
                self.get_current_deck().cost(cmdw[2], d_num)
            elif cmdw[0] == 'gen':
                d_num = int(cmdw[1])
                d_type = cmdw[2]
                if d_type == 'Rand':
                    d_type = self.get_current_deck().d.random_type()
                self.get_current_deck().cost(d_type, -d_num)
                
            else:
                print(f'Not implemented cmd {cmd}')
                
   
    def on_round_finished(self):
        # update all states
        for deck in self.decks:
            deck.on_round_finished()
            
        self.current_agent = self.agent_moves_first
        self.agent_moves_first = None
            
    def print_desk(self, event=''):
        print('\n' * 3 + '=' * 50)
        print(f"[Round {self.round_num:02d}] {event}")
        print('-' * 50)
        for i, d in enumerate(self.decks):
            print(f'Player {i + 1} ' + ('<*>' if self.current_agent == i else ''))
            d.print_deck()
            if self.current_agent == i:
                print('Available actions:')
                d.print_actions()
            print('-' * 50)
            
        
    def game_loop(self, show=False):
        # round start
        while self.check_win() < 0 and self.round_num < 3:
            # start a new round
            self.round_num += 1
            # pull cards
            for i in self.decks:
                i.pull()
            
            if show:
                self.print_desk('Pull cards')
            # throw dices
            for a, d in zip(self.agents, self.decks):
                d.roll()
                keep_dice = a.get_keep_dice(self.state())
                d.reroll(keep=keep_dice)
                
            if show:
                self.print_desk('Roll & Reroll')
                
            while True:
                self.switch_agent = False
                agent = self.agents[self.current_agent]
                action = agent.get_action(self.state())
                self.parse_action(action)
                
                if show:
                    self.print_desk(f'Player {self.current_agent + 1} exec: ' + action)
                ret = self.check_win()
                if ret >= 0:
                    return ret
                if self.is_round_finished():
                    break
                if self.switch_agent:
                    self.next_agent()
                    
                
                
            # one round finished
            self.on_round_finished()
            if show:
                self.print_desk('round finished')
            
        return max(self.check_win(), 0)
        
        
    def print_winner(self, ret):
        print('\n' * 3 + '=' * 20)
        if ret != 0:
            print(f'Game finished. The winner is Player {ret + 1}')
        else:
            print('Game finished. It is a draw')
        print('=' * 20)
        
        
if __name__ == '__main__':
    g = Game([Deck('p1'), Deck('p1')], [Agent(), Agent()])
    ret = g.game_loop(show=True)
    g.print_winner(ret)
    