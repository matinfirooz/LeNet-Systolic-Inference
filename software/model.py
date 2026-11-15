"""Dense LeNet matching the specification's layer table, including pooled tanh."""
import torch
from torch import nn

class LeNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1=nn.Conv2d(1,6,5)
        self.conv3=nn.Conv2d(6,16,5)
        self.conv5=nn.Conv2d(16,120,5)
        self.fc6=nn.Linear(120,84)
        self.fc7=nn.Linear(84,10)
    def forward(self,x):
        x=torch.tanh(self.conv1(x))
        x=torch.tanh(nn.functional.avg_pool2d(x,2))
        x=torch.tanh(self.conv3(x))
        x=torch.tanh(nn.functional.avg_pool2d(x,2))
        x=torch.tanh(self.conv5(x)).flatten(1)
        return self.fc7(torch.tanh(self.fc6(x)))
    def probabilities(self,x):
        return torch.softmax(self(x),dim=1)

def prepare_pixels(raw):
    x=torch.as_tensor(raw.copy()).float().unsqueeze(1)/255.0
    return nn.functional.pad(x,(2,2,2,2),value=0.0)
