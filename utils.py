import json
import numpy as np

def load_js(name, prefix=''):
    with open(prefix + name + '.json', 'r') as f:
        return json.load(f)

def dump_js(name, data, prefix=''):
    with open(prefix + name, 'w') as f:
        json.dump(data, f, indent = 4)

def get_project_progress():
    names = ['Characters', 'Actions']
    print('Card progress')
    for name in names:
        print(f"[{name}] {len(load_js(name))} / {len(load_js('todo_' + name))}")

def to_code_name(s):
    return s.lower().strip().replace(' ', '_')
        
def count_total_dice(dices):
    c = 0
    for i in dices:
        c += dices[i]
    return c
    
def _is_affordable_single(d_type, d_num, dice):
    # check dice limit
    if d_type == 'Matching':
        for i in dice:
            if i == 'Omni':
                continue
            if dice[i] + dice['Omni'] >= d_num:
                break
        else:
            return False
    elif d_type == 'Unaligned':
        if d_num > count_total_dice(dice):
            return False
    else:
        if d_num > dice[d_type]:
            return False
    return True
    
def is_affordable(cost, dice, character):
    if cost['p_num'] > character.power:
        return False
        
    for d_type, d_num in zip(cost['d_type'], cost['d_num']):
        if not _is_affordable_single(d_type, d_num, dice):
            return False
    
    return True

def build_cost(d_num):
    return {
        'd_num': d_num,
        'p_num': 0,
        'd_type': 'Unaligned',
    }


def _generate_action_space(cost, dice, character):
    res = ''
    if cost['p_num'] > character.power:
        return []
    elif cost['p_num'] > 0:
        res = f"cost {cost['p_num']} power"
    if sum(cost['d_num']) == 0:
        return ['cost 0 Omni;' + res] if len(res) else ['cost 0 Omni']
    if sum(cost['d_num']) > count_total_dice(dice):
        return []

    global_solutions = None
    
    for d_type, d_num in zip(cost['d_type'], cost['d_num']):
        # solution for one cost requirement
        if d_type == 'Matching':
            local_solutions = []
            for i in dice:
                if i == 'Omni':
                    continue
                local_solutions.extend([{i: t, 'Omni': d_num - t} for t in range(dice[i] + 1) if d_num - t <= dice['Omni'] and d_num - t >= 0])
                
        elif d_type == 'Unaligned':
            if d_num > count_total_dice(dice):
                return []
            
            # iteratively solve the issue
            def generate_unaligned_action_space(num_needed, dices, visited=[]):
                # print('Iter', dices, num_needed, visited)
                if num_needed < 1: # in case i'm stupid
                    return [{}]
                if num_needed == 1:
                    return [{i: 1} for i in dices if i not in visited]
                else:
                    res = []
                    for i in dices:
                        if dices[i] > 0 and i not in visited:
                            next_dice = {j: dices[j] for j in dices}
                            next_dice[i] -= 1
                            # print('IterIter', dices, num_needed)
                            next_action_spaces = generate_unaligned_action_space(num_needed - 1, next_dice, visited)
                            # add this iteration
                            for next_action_space in next_action_spaces:
                                next_action_space[i] = next_action_space.get(i, 0) + 1
                            res.extend(next_action_spaces)
                            visited.append(i)
                            
                    return res
            local_solutions = generate_unaligned_action_space(d_num, dice)
                
        else:
            if d_num > dice[d_type]:
                return []
            else:
                local_solutions = [{d_type: d_num}]
                
        # print(f'Local ask {d_type} {d_num}', local_solutions)
        # merge solutions and check
        if global_solutions is None:
            global_solutions = local_solutions
        else:
            temp_solutions = []
            for global_solution in global_solutions:
                for local_solution in local_solutions:
                    temp_solution = {i:global_solution[i] for i in global_solution}
                    for i in local_solution:
                        # print(global_solution, i )                   
                        temp_solution[i] = global_solution.get(i, 0) + local_solution[i]
                        # cost too much
                        if dice[i] < temp_solution[i]:
                            break
                    else:
                        temp_solutions.append(temp_solution)
            # print('Temp', temp_solutions)
            global_solutions = temp_solutions
        # print('Global',len(global_solutions), global_solutions)
    return [
        ';'.join([f"cost {g[i]} {i}" for i in g if g[i] > 0] + ([res] if len(res) else []))
        for g in global_solutions
        ]

def generate_action_space(cost, dice, character, prefix=None):
    res = _generate_action_space(cost, dice, character)
    if prefix is None:
        return res
    if isinstance(prefix, str):
        prefix = [prefix]
    # print(res, prefix)
    return [';'.join([i, j]) for i in res for j in prefix]

def print_dice(dice):
    res ='| '.join([f"{i}: {dice[i]}" for i in dice if dice[i] > 0])
    print(res)
    return res
 
 
if __name__ == '__main__':
    get_project_progress()