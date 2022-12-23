from utils import *
from deck import Deck
from agent import Agent
import random


class Game:
    def __init__(self, decks):
        assert len(decks) == 2
        self.decks = decks
        for i in range(2):
            self.decks[i].enemy_ptr = self.decks[1 - i]
            self.decks[i].game_ptr = self
            self.decks[i].deck_id = i
        self.agents = [i.agent for i in decks]
        self.agent_num = len(decks)
        self.round_num = 0
        self.agent_moves_first = None
        self.current_agent = 0
        self.finish_round = [False] * self.agent_num

        self.switch_agent = False
        self.action_history = []

    """
    Save, load, states and prints
    """
    def save(self):
        game_state = {
            'round_num': self.round_num,
            'agent_moves_first': self.agent_moves_first,
            'current_agent': self.current_agent,
            'finish_round': self.finish_round,
            'switch_agent': self.switch_agent,
            'action_history': self.action_history
        }
        game_state['decks'] = [d.save() for d in self.decks]
        return game_state
            
    def state(self):
        return {
                'my_state': self.get_current_deck().state(),
                'other_state': self.get_other_deck().state_for_enemy()
            }
            
    def state_for_action(self):
        res = self.state()
        res['action_space'] = self.get_current_deck().get_action_space()
        return res

    def state_only_mine(self):
        return  {
            'my_state': self.get_current_deck().state(),
            'other_state': None,
        }

    def print_desk(self, event=''):
        # print(self.state())
        print('\n' * 3 + '=' * 50)
        print(f"[Round {self.round_num:02d}] {event}")
        print('-' * 50)
        for i, d in enumerate(self.decks):
            print(f'Player {i + 1} ' + ('[√]' if self.finish_round[i] else '[ ]') + (' <*>' if self.current_agent == i else ''))
            d.print_deck()
            print('-' * 50)
   
    def print_full_desk(self, event=''):
        print('\n' * 3 + '=' * 50)
        print(f"[Round {self.round_num:02d}] {event}")
        print('-' * 50)
        for i, d in enumerate(self.decks):
            print(f'Player {i + 1} ' + ('[√]' if self.finish_round[i] else '[ ]') + (' <*>' if self.current_agent == i else ''))
            d.print_deck()
            print('Available actions:')
            d.print_actions()
            print('-' * 50)

    def print_winner(self, ret):
        print('\n' * 3 + '=' * 20)
        if ret > 0:
            print(f'Game finished. The winner is Player {ret}')
        else:
            print('Game finished. It is a draw')
        print('=' * 20)

    """
    Get status
    """

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

    
    def get_current_deck(self):
        return self.decks[self.current_agent]
        
    def get_other_deck(self):
        for i, j in enumerate(self.decks):
            if i != self.current_agent:
                return j
        
    """
    Engine pipeline
    """ 
    def _proc_skill(self, cmdw):
        my_deck = self.get_current_deck()
        my_char = my_deck.get_character(cmdw[1])
        enemy_char = self.get_other_deck().get_current_character()
        my_char.get_skill(cmdw[2]).exec(my_deck, my_char, enemy_char)
        self.switch_agent = True

    def engine_support(self, action, idx):
        cur_deck = self.get_current_deck()
        cur_deck.add_support(action, idx)

    def engine_equipment(self, action, target):
        code_name = action.code_name
        cur_deck = self.get_current_deck()
        target_char = cur_deck.get_character(target)
        if target_char is None:
            # for buff without a specific target
            target_char = cur_deck.get_current_character()
        cmds = action.code.split(';')
        for cmd in cmds:
            cmdw = cmd.split()
            if cmdw[0] == 'skill':
                self._proc_skill(cmdw)
            elif cmdw[0] == 'talent':
                assert target_char.code_name in cmdw[1]
                target_char.add_talent(cmd)
            elif cmdw[0] == 'buff':
                target_char.add_buff(code_name, cmd)
            elif cmdw[0] == 'weapon':
                target_char.add_weapon(action, cmd)
            elif cmdw[0] == 'artifact':
                target_char.add_artifact(action, cmd)
            elif cmdw[0] == 'shield':
                try:
                    target_char.add_shield(code_name, int(cmdw[1]))
                except ValueError:
                    value = cur_deck.count_character_by_faction(cmdw[1])
                    target_char.add_shield(code_name, value)

    def engine_event(self, action, target):
        code_name = action.code_name
        my_deck = self.get_current_deck()
        target_char = my_deck.get_character(target)
        if target_char is None:
            # for buff without a specific target
            target_char = my_deck.get_current_character()
        cmds = action.code.split(';')
        for cmd in cmds:
            cmdw = cmd.split()
            if cmdw[0] == 'heal':
                target_char.heal(int(cmdw[1]))
            elif cmdw[0] == 'heal_other':
                for c in my_deck.get_other_characters():
                    c.heal(int(cmdw[1]))
            elif cmdw[0] == 'heal_summon':
                my_deck.get_summon(target).heal(int(cmdw[1]))
            elif cmdw[0] == 'kill_summon':
                my_deck.enemy_ptr.get_summon(target)
            elif cmdw[0] == 'kill_all_summons':
                my_deck.kill_all_summons()
                my_deck.enemy_ptr.kill_all_summons()
            elif cmdw[0] == 'recharge':
                my_deck.recharge(cmdw)
            elif cmdw[0] == 'buff':
                target_char.add_buff(code_name, cmd)
            elif cmdw[0] == 'gen':
                my_deck.gen(cmdw[2], int(cmd[1]))
            # use card to switch characters
            elif cmdw[0] == 'switch_my':
                my_deck.activate(target)
            elif cmdw[0] == 'draw':
                my_deck.pull(int(cmdw[1]))
            elif cmdw[0] == 'reroll':
                for _ in range(int(cmdw[1])):
                    my_deck.reroll()
            elif cmdw[0] == 'summon_rand':
                my_deck.add_rand_summon(code_name, int(cmdw[1]), cmdw[2:])
            else:
                raise NotImplementedError(f'[engine_event]{cmd}')

        if 'food' in action.tags:
            for s in my_deck.supports:
                # Chef Mao and nre
                if s.query('on_food_event') == 0:
                    continue
                target_char._engine_buff(s)

    def parse_space_action(self, action):
        self.action_history.append(f'Player {self.current_agent + 1}: {action}')
        if action in ['finish', '']:
            self.finish_round[self.current_agent] = True
            # player who finishes first moves first in the next round
            if self.agent_moves_first is None:
                self.agent_moves_first = self.current_agent
            self.switch_agent = True
            return   

        my_deck = self.get_current_deck() 
        cmds = action.split(';')
        for cmd in cmds:
            cmdw = cmd.split()
            if cmdw[0] == 'event':
                action = my_deck.use_card(cmdw[1])
                # not all events have a target
                self.engine_event(action, cmdw[2] if len(cmdw) > 2 else None)
            elif cmdw[0] == 'equipment':
                action = my_deck.use_card(cmdw[1])
                # not all events have a target
                self.engine_equipment(action, cmdw[2] if len(cmdw) > 2 else None)
            elif cmdw[0] == 'support':
                action = my_deck.use_card(cmdw[1])
                self.engine_support(action, int(cmdw[2])) # index of the support will be
            elif cmdw[0] == 'convert':
                action = my_deck.use_card(cmdw[1])
            elif cmdw[0] == 'skill':
                self._proc_skill(cmdw)
            elif cmdw[0] == 'cost':
                my_deck.cost(cmdw[2], int(cmdw[1]))
            elif cmdw[0] == 'gen':
                my_deck.gen(cmdw[2], int(cmd[1]))
            elif cmdw[0] == 'activate':
                # this is only used when a character is defeated
                my_deck.activate(cmdw[1])
                self.switch_agent = True
            elif cmdw[0] == 'reroll':
                for _ in range(int(cmdw[1])):
                    my_deck.reroll()
            elif cmdw[0] == 'switch':
                my_char = my_deck.get_current_character()
                res = my_char.take_buff('switch_fast') + my_deck.take_support_buff('switch_fast')
                self.switch_agent = res == 0
                my_deck.activate(cmdw[1])
            elif cmdw[0] == 'transfer':
                my_deck.transfer_equip(cmdw[1], cmdw[2], cmdw[3])   
            else:
                raise NotImplementedError(f'[parse_space_action]{cmd}')
                
    """
    Round events
    """

    def on_round_start(self):
        # clear states
        self.finish_round = [False] * self.agent_num
        
        # update all states
        for deck in self.decks:
            deck.on_round_start()
   
    def on_round_finished(self):
        # update all states
        for deck in self.decks:
            deck.on_round_finished()
        
        # check if character dead
        self.has_alive_changed()
        self.current_agent = self.agent_moves_first
        self.agent_moves_first = None
        
    def has_alive_changed(self):
        for t in range(2):
            i = t - abs(self.current_agent)  # start from the current_agent first
            d = self.decks[i]
            # If need to switch character (someone is defeated and no one is active)
            if d.has_alive_changed() and not d.has_active_character():
                print(f'\n\nPlayer {i + 1} needs to switch character')
                d.print_actions()
                # ask user to activate a new character
                agent = self.agents[i]
                action = agent.get_action(self.state_for_action())
                self.parse_space_action(action)
            
    
    def game_loop(self, show=False, save_hist=False):
        # init the game
        for i in self.decks:
            # draw 5 init cards
            i.shuffle()
            i.pull(5)
            
            # swap init cards
            if show:
                self.print_desk(f'Player {self.current_agent + 1} init cards')
            if save_hist:
                dump_js(f'states/R{self.round_num:02d}_00_draw_card', self.save())
                
            keep_card = i.agent.get_keep_card(self.state_only_mine())
            i.swap_card(keep_card)

            if save_hist:
                dump_js(f'states/R{self.round_num:02d}_01_swap_card', self.save())

            # select the first character
            s = self.state_only_mine()
            s['action_space'] = [f"activate {i.code_name}" for i in i.characters]
            action = i.agent.get_action(s)
            self.parse_space_action(action)
            
            if show:
                self.print_full_desk(f'Player {self.current_agent + 1} swap cards ' + ','.join([str(i) for i in keep_card]))
            if save_hist:
                dump_js(f'states/R{self.round_num:02d}_02_activate', self.save())
            self.next_agent()

        # round start
        while self.check_win() < 0 and self.round_num < 15:
            # start a new round
            self.round_num += 1
            self.on_round_start()
            t = 0
            while True:
                self.switch_agent = False
                
                tmp = self.current_agent

                if save_hist:
                    dump_js(f'states/R{self.round_num:02d}_{t:02d}_before', self.save())

                agent = self.agents[self.current_agent]
                action = agent.get_action(self.state_for_action())
                self.parse_space_action(action)
                
                ret = self.check_win()
                if ret >= 0:
                    if show:
                        self.print_desk(f'Player {tmp + 1} exec: ' + action)
                    if save_hist:
                        dump_js(f'states/R{self.round_num:02d}_{t:02d}_done', self.save())
                    return ret
                    
                self.has_alive_changed()
                if self.is_round_finished():
                    break
                if self.switch_agent:
                    self.next_agent()
                    
                if show:
                    self.print_full_desk(f'Player {tmp + 1} exec: ' + action)
                if save_hist:
                    dump_js(f'states/R{self.round_num:02d}_{t:02d}_done', self.save())
                t += 1

            # one round finished
            self.on_round_finished()
            if show:
                self.print_desk('round finished')
            if save_hist:
                dump_js(f'states/R{self.round_num:02d}_{t:02d}_round_finished', self.save())

        return self.check_win()
        
        
        
if __name__ == '__main__':
    g = Game([Deck('p1', Agent()), Deck('p2', Agent())])
    ret = g.game_loop(show=False)
    g.print_winner(ret)
    