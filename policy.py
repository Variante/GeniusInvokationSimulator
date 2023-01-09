from deck import Deck
from agent import LearnedAgent
from policynetwork import QNetwork
from transformers import BertTokenizer, BertModel
import torch.nn.functional as F
import torch.optim as optim

def make_policy_network(args):
    return QNetwork(
        n_token: args.state_tokens + 1, # state tokens + action token
        d_model: args.state_embeding, # this is 768 in N x 768 state, as well as action
        n_layer: args.num_layers, # number of layers
        n_head: args.num_heads, # number of heads
        d_hid: args.dim_hidden_layers, # dimension of the feedforward network model in nn.TransformerEncoder
        dropout: args.q_dropout
    )

def soft_update_params(net, target_net, tau):
    for param, target_param in zip(net.parameters(), target_net.parameters()):
        target_param.data.copy_(
            tau * param.data + (1 - tau) * target_param.data
        )


class DQNPolicy:
    def __init__(self, args, rb, device):
        self.args = args
        self.rb = rb
        self.device = device
        self.gamma = args.discount_factor
        self.tau = args.encoder_tau
        

        # decks for game play
        self.deck1 = Deck(args.agent_deck_name, LearnedPolicy(self.inference))
        self.deck2 = Deck(args.agent_deck_name, LearnedPolicy(self.inference))

        # bert for text embedding
        self.tokenizer = BertTokenizer.from_pretrained(args.pretrain_model_name)
        self.pretrain_model = BertModel.from_pretrained(args.pretrain_model_name).to(device)
        self.pretrain_model.eval()

        # init Q networks
        self.online_net = make_policy_network(args).to(device)
        self.target_net = make_policy_network(args).to(device)
        self.target_net.copy_weights_from(self.online_net)

        # optimizer
        self.optimizer = optim.Adam(
            self.online_net.parameters(), lr=args.lr, betas=(args.lr_beta, 0.999)
        )

        self.training = False

    def train(self, training: bool):
        self.training == training
        if training:
            self.online_net.train()
        else:
            self.online_net.eval()

    def get_text_embedding(self, texts):
        # texts is a list of strings
        encoded_input = self.tokenizer(texts, padding=True, return_tensors="pt")
        input_ids = encoded_input['input_ids'].to(self.device)
        attention_mask = encoded_input['attention_mask'].to(self.device)
        token_type_ids = encoded_input['token_type_ids'].to(self.device)
        # Predict hidden states features for each layer
        with torch.no_grad():
            # See the models docstrings for the detail of the inputs
            outputs = model(input_ids, attention_mask=attention_mask , token_type_ids=token_type_ids)
            # PyTorch-Transformers models always output tuples.
            # See the models docstrings for the detail of all the outputs
            # In our case, the first element is the hidden state of the last layer of the Bert model
            encoded_layers = outputs[0] # batch (which is len(state_str)=N) x ? x 768
            return torch.mean(encoded_layers, dim=1) # batch (N) x 768

    def model_forward(self, state_embedding, action_space_embedding, use_target=False):
        # prepare for the online network [seq_len (N + 1), batch_size(action space size m), 768]
        """
        # Method 1
        state_action = torch.zeros([state_embedding.shape[0] + 1, action_space_embedding.shape[0], state_embedding.shape[1]])
        for i in range(action_space_embedding.shape[0]):
            state_action[:-1, i] = state_embedding # copy state
            state_action[-1, i] = action_space_embedding[i]
        """
        # Method 2
        state_stack = state_embedding.unsqueeze(1).repeat(1, action_space_embedding.shape[0], 1) # N * m * 768
        action_stack = action_space_embedding.unsqueeze(0) #  1 * m * 768
        state_action = torch.concat([state_embedding, action_stack], dim=0) # N+1 * m * 768

        if use_target:
            net = self.target_net
        else:
            net = self.online_net

        # inference
        with torch.no_grad():
            # it requires [seq_len (N + 1), batch_size(action space size m), 768]
            q_values = net(state_action) # should be
        action_idx = torch.argmax(q_values.reshape(-1))[0].item()
        
        return {
            'action_idx': action_idx, # int
            'action': action_space_embedding[action].cpu() # action embedding
            'q_values': q_values
        }

    def _update_networks(self):
        samples = self.rb.sample_batch()
        state_embedding = samples['state'].to(self.device) # B, N, 768
        next_state_embedding = samples['next_state'].to(self.device) # B, N, 768
        action_embedding = samples['action'].to(self.device) # B, 768
        next_action_space_embedding = samples['action_space']
        reward = samples['reward'].reshape(-1, 1).to(self.device)
        done = samples['done'].reshape(-1, 1).to(self.device)

        # state embedding -> N, B, 768 action embedding -> 1, B, 768
        curr_state_action = torch.concat([state_embedding.permute(1, 0, 2), action_embedding.unsqueeze(0)], dim=0) # N+1 * B * 768

        # it requires [seq_len (N + 1), batch_size(action space size m), 768]
        curr_q_value = self.online_net(curr_state_action) # B, 1
        assert next_state_embedding.shape[0] == len(next_action_space_embedding)
        next_q_value_list = [self.model_forward(next_state_embedding[i], next_action_space_embedding[i], use_target=True)['q_values'] for i in range(len(next_action_space_embedding))]
        # [shape (1, 1)] * B
        next_q_value = torch.concat(next_q_value_list, dim=0)
        # bellman eq. target B, 1
        target = reward + self.gamma * next_q_value * (1 - done)
        
        # L1 loss
        loss = F.smooth_l1_loss(curr_q_value, target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        # move target network
        soft_update_params(self.online_net.transformer_encoder, self.target_net.transformer_encoder, self.tau)
        soft_update_params(self.online_net.decoder, self.target_net.decoder, self.tau)


    def inference(self, state_str, action_space_str, info):
        # current state embedding
        state_embedding = self.get_text_embedding(state_str) # N x 768
        # current action space
        action_space_embedding = self.get_text_embedding(action_space_str) # m x 768
        # get results for current step
        results = self.model_forward(state_embedding, action_space_embedding)
        results['state'] = state_embedding.cpu(), # cpu tensor
        results['action_space'] = action_space_embedding.cpu(), # cpu tensor

        # gather sample
        if info['state'] is not None:
            # for next state, and its action space
            next_state = results['state']
            action_space = results['action_space']

            # for current state (it comes from last step)
            current_state = info['state']
            action = info['action']
            reward = info['reward']
            done = info['done']

            self.rb.add(
                current_state,
                action,
                action_space,
                reward,
                next_state,
                done
            )

        # train the network if necessary
        if self.training:
            self._update_networks()
        return results
        

    def get_deck(self):
        return self.deck1, self.deck2

    def save(self, model_dir, step):
        import os
        torch.save(
            self.online_net.state_dict(), os.path.join(model_dir, f'online_{step:d}.pt')
        )
        torch.save(
            self.target_net.state_dict(), os.path.join(model_dir, f'target_{step:d}.pt')
        )

    def load(self, model_dir, step):
        import os
        self.online_net.load_state_dict(
            torch.load(os.path.join(model_dir, f'online_{step:d}.pt'))
        )
        self.target_net.load_state_dict(
            torch.load(os.path.join(model_dir, f'target_{step:d}.pt'))
        )


