import numpy as np
import torch

# borrowed from https://github.com/Curt-Park/rainbow-is-all-you-need/blob/master/08.rainbow.ipynb

class ReplayBuffer:
    """A simple numpy replay buffer."""

    def __init__(
        self, 
        obs_dim: tuple, # lines x embedding: N x 768
        act_dim: int, # 768
        size: int, 
        batch_size: int
    ):
        self.obs_buf = torch.empty([size, *obs_dim], dtype=torch.float32, pin_memory=True) 
        # it will hold b x N X 768 embeddings
        self.next_obs_buf = torch.empty([size, *obs_dim], dtype=torch.float32, pin_memory=True)
        # it will hold b x N X 768 embeddings
        self.acts_buf = torch.empty([size, act_dim], dtype=torch.float32, pin_memory=True)
        # it will hold b x 768 embeddings
        self.acts_space_buf = [None] * size # it will hold b x m x 768 embeddings
        self.rews_buf = torch.empty(size, dtype=torch.float32, pin_memory=True)
        self.done_buf = torch.empty(size, dtype=torch.float32, pin_memory=True)
        self.max_size, self.batch_size = size, batch_size
        self.ptr, self.size, = 0, 0
        self.full = False

    def add(
        self, 
        obs: torch.Tensor, 
        act: torch.Tensor, 
        acts_space: torch.Tensor, 
        rew: float, 
        next_obs: torch.Tensor, 
        done: bool,
    ):
        self.obs_buf[self.ptr] = obs
        self.next_obs_buf[self.ptr] = next_obs
        self.acts_buf[self.ptr] = act
        self.acts_space_buf[self.ptr] = self.acts_space
        self.rews_buf[self.ptr] = torch.FloatTensor([rew])
        self.done_buf[self.ptr] = torch.FloatTensor([1] if done else [0])
        self.ptr = (self.ptr + 1) % self.max_size
        self.size = min(self.size + 1, self.max_size)


    def sample_batch(self):
        idxs = np.random.choice(self.size, size=self.batch_size, replace=False)
        return self.sample_batch_from_idxs(idxs)
    
    def sample_batch_from_idxs(self, idxs: np.ndarray):
        return {
            "state": self.obs_buf[idxs],
            "next_state": self.next_obs_buf[idxs],
            "action": self.acts_buf[idxs],
            "action_space": [self.acts_space_buf[i] for i in idxs]
            "reward": self.rews_buf[idxs],
            "done": self.done_buf[idxs]
        }

    def __len__(self) -> int:
        return self.size
