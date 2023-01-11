import os
import random
import numpy as np
import torch
import argparse
from datetime import datetime
from tqdm import tqdm, trange
from game import *
from agent import RandomAgent
from agent_dqn import DQNAgent as MyAgent
from replaybuffer import ReplayBuffer
import git

from tensorboardX import SummaryWriter


def set_seed_everywhere(seed):
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)


def evaluate(env, agent, enemy_deck, writer, args, global_episode):
    writer.add_text('train.py', 'evaluate', agent.step_num)
    agent.train(False)
    # change to eval policy
    env.set_new_deck(1, enemy_deck)
    hists = [0] * 3
    with trange(args.num_eval_episodes) as t:
        for episode in t:
            save_state = episode == 0 and args.save_first_eval_episode
            ret = env.game_loop(show=False, save_state=(os.path.join(args.episode_dir, f'Step-{agent.step_num:09d}') if save_state else False))
            env.reset()
            hists[ret] += 1

            # Description will be displayed on the left
            t.set_description(f'E | Ep: {global_episode} S: {agent.step_num} | W/D/L/Total: {hists[0]}/{hists[-1]}/{hists[1]}/{episode + 1}')

    # update log
    writer.add_scalar('eval/win_rate', hists[0] / args.num_eval_episodes, agent.step_num)
    writer.add_scalar('eval/win', hists[0], agent.step_num)
    writer.add_scalar('eval/lose', hists[1], agent.step_num)
    writer.add_scalar('eval/draw', hists[-1], agent.step_num)

    writer.add_scalar('eval_episode/win_rate', hists[0] / args.num_eval_episodes, global_episode)
    writer.add_scalar('eval_episode/win', hists[0], global_episode)
    writer.add_scalar('eval_episode/lose', hists[1], global_episode)
    writer.add_scalar('eval_episode/draw', hists[-1], global_episode)

    if args.save_buffer:
        writer.add_text('train.py', 'save rb to', agent.step_num)
        # TODO write save buffer

    if args.save_model:
        agent.save(args.model_dir)
        writer.add_text('train.py', 'save model to ' + os.path.join(model_dir, f'online_{self.step_num:d}.pt'), agent.step_num)

    # change back to training config
    env.set_new_deck(1, agent.get_deck()[1])
    agent.train(True)


def parse_args():
    parser = argparse.ArgumentParser()
    # env
    parser.add_argument('--agent_deck_name', default='starter', type=str)
    parser.add_argument('--pretrain_model_name', default='prajjwal1/bert-tiny', type=str)
    parser.add_argument('--state_tokens', default=54, type=int)
    parser.add_argument('--state_embeding', default=128, type=int)
    # replay buffer
    parser.add_argument('--replay_buffer_capacity', default=100000, type=int)
    parser.add_argument('--epsilon', default=0.1, type=float)
    # train
    parser.add_argument('--init_steps', default=2000, type=int)
    parser.add_argument('--num_train_episode', default=10000, type=int)
    parser.add_argument('--batch_size', default=512, type=int)
    parser.add_argument('--discount_factor', default= 0.99, type=float)
    # eval
    parser.add_argument('--eval_freq', default=50, type=int)
    parser.add_argument('--num_eval_episodes', default=10, type=int)
    # value network
    parser.add_argument('--lr', default=1e-4, type=float)
    parser.add_argument('--lr_beta', default=0.9, type=float)
    parser.add_argument('--encoder_tau', default=0.05, type=float)
    parser.add_argument('--num_layers', default=1, type=int)
    parser.add_argument('--num_heads', default=4, type=int)
    parser.add_argument('--dim_hidden_layers', default=128, type=int)
    parser.add_argument('--q_dropout', default=0.1, type=float)
    # misc
    parser.add_argument('--seed', default=-1, type=int)
    parser.add_argument('--work_dir', default='./runs', type=str)
    parser.add_argument('--save_first_eval_episode', default=False)
    parser.add_argument('--save_buffer', default=False)
    parser.add_argument('--save_model', default=False)
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    if args.seed == -1:
        args.__dict__["seed"] = np.random.randint(0,1000000)

    set_seed_everywhere(args.seed)

    gitsha = git.Repo(search_parent_directories=True).head.object.hexsha[:6]
    task_title = f'DQN-MLP-c{gitsha}-b{args.batch_size}-s{args.seed}-{datetime.now():%m-%d}'

    # mkdir
    args.work_dir = os.path.join(args.work_dir, task_title)
    make_dir(args.work_dir)
    args.episode_dir = make_dir(os.path.join(args.work_dir, 'episodes'))
    args.model_dir = make_dir(os.path.join(args.work_dir, 'model'))
    args.buffer_dir = make_dir(os.path.join(args.work_dir, 'buffer'))
    args.tb_dir = make_dir(os.path.join(args.work_dir, 'tb'))

    # dump config
    with open(os.path.join(args.work_dir, 'args.json'), 'w') as f:
        json.dump(vars(args), f, sort_keys=True, indent=4)

    writer = SummaryWriter(logdir=args.tb_dir, flush_secs=10)
    writer.add_text('train.py', f'Config save to {args.work_dir}', 0)

    # replay buffer
    rb = ReplayBuffer(
        obs_dim=(args.state_tokens, args.state_embeding),
        act_dim=args.state_embeding,
        size=args.replay_buffer_capacity,
        batch_size=args.batch_size
    )

    # agent
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    agent = MyAgent(args, rb, writer, device)

    # Play with itself, eval with a random policy
    env = Game(agent.get_deck())
    enemy_deck = Deck(args.agent_deck_name, RandomAgent())

    evaluated = False
    with trange(args.num_train_episode) as t:
        def update_progress():
            t.set_description(f'T | Ep: {episode} S: {agent.step_num} B: {len(rb)} | Loss: {agent.loss:.3f}')

        for episode in t:
            try:
                evaluated = False
                ret = env.game_loop(show=False, save_state=False, on_action_finished=update_progress)
                agent.episode_finished(ret)
                env.reset()
                # log
                writer.add_scalar('train/episode', episode, agent.step_num)
                update_progress()

                if episode % args.eval_freq == 0:
                    evaluate(env, agent, enemy_deck, writer, args, episode)
                    evaluated = True
            except KeyboardInterrupt:
                print('User stops the training, perform the last evaluation.')
                break

    if not evaluated:
        evaluate(env, agent, enemy_deck, writer, args, episode)
    writer.close()

if __name__ == '__main__':
    main()
