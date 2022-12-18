from utils import *
from deck import Deck
import random

class Game:
    def __init__(self, decks, agents):
        self.decks = decks
        self.agents = agents
        assert len(self.decks) == len(self.agents)
        
        self.agent_num = len(agents)
        self.round_num = 0
        self.agent_moves_first = 0
        self.current_agent = 0
        self.finish_round = [False] * agent_num
        
    def next_agent(self):
        idx = self.current_agent
        while True
            idx += 1
            idx %= self.agent_num
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
                a.name: d.state for a, d in zip(self.agents, self.decks),
                'action_space': self.decks[self.current_agent].get_action_space()
            }
            
    def parse_action(self):
        pass
            
    def game_loop(self):
        # round start
        while check_win < 0:
            # start a new round
            self.round_num += 1
            # pull cards
            for i in self.decks:
                i.pull()
            
            # throw dices
            for a, d in zip(self.agents, self.decks):
                d.roll()
                keep_dice = a.get_keep_dice(self.state())
                d.reroll()

            while not self.is_round_finished():
                agent = self.agents[self.current_agent]
                action = agent.get_action(self.state())
                self.parse_action(action)
                self.next_agent()
            # one round finished
                
