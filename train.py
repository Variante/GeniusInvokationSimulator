import os
import random
import numpy as np
import torch
import argparse
import time
from tqdm import tqdm
from game import *
from agent import RandomAgent

from policy import DQNPolicy as my_agent

from replaybuffer import ReplayBuffer

def make_dir(dir_path):
    try:
        os.mkdir(dir_path)
    except OSError:
        pass
    return dir_path

def set_seed_everywhere(seed):
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)


def parse_args():
    parser = argparse.ArgumentParser()
    # env
    parser.add_argument('--agent_deck_name', default='starter', type=str)
    parser.add_argument('--pretrain_model_name', default='bert-base-uncased', type=str)
    parser.add_argument('--state_tokens', default=20, type=int)
    parser.add_argument('--state_embeding', default=768, type=int)
    # replay buffer
    parser.add_argument('--replay_buffer_capacity', default=100000, type=int)
    # train
    parser.add_argument('--init_steps', default=1000, type=int)
    parser.add_argument('--num_train_steps', default=1000000, type=int)
    parser.add_argument('--batch_size', default=32, type=int)
    parser.add_argument('--discount_factor', default= 0.99, type=float)
    # eval
    parser.add_argument('--eval_freq', default=10000, type=int)
    parser.add_argument('--num_eval_episodes', default=1000, type=int)
    # value network
    parser.add_argument('--lr', default=1e-4, type=float)
    parser.add_argument('--lr_beta', default=0.9, type=float)
    parser.add_argument('--encoder_tau', default=0.05, type=float)
    parser.add_argument('--num_layers', default=4, type=int)
    parser.add_argument('--num_heads', default=12, type=int)
    parser.add_argument('--dim_hidden_layers', default=256, type=int)
    parser.add_argument('--q_dropout', default=0.1, type=float)
    # misc
    parser.add_argument('--seed', default=1, type=int)
    parser.add_argument('--work_dir', default='.', type=str)
    parser.add_argument('--save_tb', default=False)
    parser.add_argument('--save_each_first_episode', default=False)
    parser.add_argument('--save_buffer', default=False)
    parser.add_argument('--save_model', default=False)

    parser.add_argument('--log_interval', default=100, type=int)
    parser.add_argument('--device', default='cuda', type=str)
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    if args.seed == -1:
        args.__dict__["seed"] = np.random.randint(1,1000000)

    set_seed_everywhere(args.seed)

    task_title = f'VanillaDQN-b{args.batch_size}-s{args.seed}-{time.gmtime():%m%d}'

    # mkdir
    args.work_dir = os.path.join(args.work_dir, task_title)
    make_dir(args.work_dir)
    episode_dir = make_dir(os.path.join(args.work_dir, 'episodes'))
    model_dir = make_dir(os.path.join(args.work_dir, 'model'))
    buffer_dir = make_dir(os.path.join(args.work_dir, 'buffer'))
    # dump config
    with open(os.path.join(args.work_dir, 'args.json'), 'w') as f:
        json.dump(vars(args), f, sort_keys=True, indent=4)

    print("Start at ", args.work_dir)

    # replay buffer
    rb = ReplayBuffer(
        obs_dim=(args.state_tokens, args.state_embeding)
        act_dim=args.state_embeding,
        size=args.replay_buffer_capacity,
        batch_size=args.batch_size
    )

    # agent
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    agent = DQNPolicy(args, rb, device)

    # Play with itself, eval with a random policy
    train_env = Game(*agent.get_deck())
    test_env = Game(agent.get_deck()[0], Deck(args.agent_deck_name, RandomAgent()))




