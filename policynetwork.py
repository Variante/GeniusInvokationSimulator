import torch
import torch.nn as nn
from torch.nn import TransformerEncoder, TransformerEncoderLayer
import math

class PositionalEncoding(nn.Module):
    # from https://pytorch.org/tutorials/beginner/transformer_tutorial.html
    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 5000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, 1, d_model)
        pe[:, 0, 0::2] = torch.sin(position * div_term)
        pe[:, 0, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor, shape [seq_len, batch_size, embedding_dim]
        """
        x = x + self.pe[:x.size(0)]
        return self.dropout(x)

class QNetwork(nn.Module):
    def __init__(
        self,
        n_token: int, # state tokens + action token
        d_model: int = 768, # this is 768 in N x 768 state, as well as action
        n_layer: int = 4, # number of layers
        n_head: int = 12, # number of heads
        d_hid: int = 256, # dimension of the feedforward network model in nn.TransformerEncoder
        dropout: float = 0.1
    ):
        """Initialization."""
        super().__init__()

        self.model_type = 'Transformer'
        self.n_layer = n_layer
        self.pos_encoder = PositionalEncoding(d_model, dropout, max_len=n_token)
        encoder_layers = TransformerEncoderLayer(d_model, n_head, d_hid, dropout)
        self.transformer_encoder = TransformerEncoder(encoder_layers, n_layer)
        # self.d_model = d_model
        # self.decoder = nn.Linear(d_model, n_token)
        # avg all tokens and project to one Q value
        self.decoder = nn.Linear(d_model, 1)

        self.act = nn.Sequential(
                    nn.LayerNorm(n_token),
                    nn.ReLU(),
                )

        self.decoder2 = nn.Linear(n_token, 1)
        self.init_weights()

    def init_weights(self) -> None:
        initrange = 0.1
        # self.encoder.weight.data.uniform_(-initrange, initrange)
        # self.decoder.bias.data.zero_()
        self.decoder.weight.data.uniform_(-initrange, initrange)
        self.decoder2.weight.data.uniform_(-initrange, initrange)

    def forward(self, src: torch.Tensor) -> torch.Tensor:
        """
        Args:
            src: Tensor, shape [seq_len, batch_size, embedding_dim]
        Returns:
            output Tensor of shape [batch_size, 1]
        """
        # src = self.pos_encoder(src)
        # output = self.transformer_encoder(src) # ignore mask
        # output = torch.mean(output, dim=0)
        # output shape [seq_len, batch_size, embedding_dim] => [batch_size, embedding_dim]

        output = self.decoder(src)
        output = output.squeeze(2).permute(1, 0)
        output = self.act(output)
        output = self.decoder2(output)
        # [seq_len, batch_size, embedding_dim] => [seq_len, batch_size, 1] => [batch_size, seq_len]
        return output

    def copy_weights_from(self, src):
        self.transformer_encoder.load_state_dict(src.transformer_encoder.state_dict())
        self.decoder.load_state_dict(src.decoder.state_dict())


