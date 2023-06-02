import random
from enum import Enum, IntEnum, unique
from itertools import cycle, combinations, product
from collections import Counter
import numpy as np
import copy
import pickle

from jaipur import *
from player import *


if __name__ == "__main__":
    random_strategy = RandomPlayerStrategy()
    interactive_strategy = InteractivePlayerStrategy()
    balanced_strategy = BalancedPlayerStrategy()
    game = Jaipur(lambda tag, game: Player(interactive_strategy, tag, game),
                  lambda tag, game: Player(random_strategy, tag, game),
                  muted=False)
    game.play_game()
