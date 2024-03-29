import random
from enum import Enum, IntEnum, unique
from itertools import cycle, combinations, product
from collections import Counter
import numpy as np
import copy
import pickle


@unique
class Action(IntEnum):
    TAKE = 0
    SELL = 1
    TRADE = 2


@unique
class Commodity(IntEnum):
    CAMEL = 0
    LEATHER = 1
    SPICE = 2
    SILK = 3
    SILVER = 4
    GOLD = 5
    DIAMOND = 6

    @classmethod
    def is_precious(self, commodity):
        return commodity in [self.DIAMOND, self.GOLD, self.SILVER]


class Jaipur:

    def __init__(self, player1_type, player2_type, muted=False):
        self.muted = muted

        self.price_tokens = {
            Commodity.DIAMOND:  [5, 5, 5, 7, 7],
            Commodity.GOLD:     [5, 5, 5, 6, 6], 
            Commodity.SILVER:   [5, 5, 5, 5, 5], 
            Commodity.SILK:     [1, 1, 2, 2, 3, 3, 5], 
            Commodity.SPICE:    [1, 1, 2, 2, 3, 3, 5], 
            Commodity.LEATHER:  [1, 1, 1, 1, 1, 1, 2, 3, 4], 
        }

        self._deck = [Commodity.DIAMOND] * 6 + [Commodity.GOLD] * 6 + [Commodity.SILVER] * 6 + \
                       [Commodity.SILK] * 8 + [Commodity.SPICE] * 8 + [Commodity.LEATHER] * 10 + \
                       [Commodity.CAMEL] * 8 #8 camels + 3 camels in market (11 total)
        random.shuffle(self._deck)

        self.market = Counter()
        for i in Commodity:
            self.market[i] = 0

        self.market[Commodity.CAMEL] = 3

        for i in range(2):
            self.market[self._deck.pop()] += 1

        self._player1 = player1_type(tag='P1', game=self)
        self._player2 = player2_type(tag='P2', game=self)

        # Deal 5 cards to each player
        for i in range(5):
            for _player in self._player1, self._player2:
                commodity = self._deck.pop()
                if commodity == Commodity.CAMEL:
                    _player.camel_count += 1
                else:
                    _player.hand[commodity] += 1

        self.winner = None
        self._players_gen = cycle([self._player1, self._player2]) 
        self.player_turn = next(self._players_gen)

    def pick_commodity(self, commodity=None):
        if sum(self.market.values()) == 0: #Assert
            return (None, 0)

        if commodity is not None and self.market[commodity] > 0: #Assert
            picked_commodity = commodity
        else:
            market_list = []
            for c in self.market:
                if self.market[c] > 0:
                    market_list += [c] * self.market[c]

            picked_commodity = random.choice(market_list)
                
        pick_count = 0

        # When player takes camel, all camels in market must be taken
        if picked_commodity == Commodity.CAMEL:
            market_camels = self.market[Commodity.CAMEL]
            pick_count = market_camels 
            self.market[Commodity.CAMEL] = 0

            for i in range(market_camels):
                if self._deck:
                    self.market[self._deck.pop()] += 1

        else:
            pick_count = 1
            self.market[picked_commodity] -= 1
            if self._deck:
                self.market[self._deck.pop()] += 1

        return (picked_commodity, pick_count)

    # print hand or market with less clutter
    def pprint(self, s, c):
        print(s, end=' ')
        for i in c.keys():
            if c[i] > 0:
                print('%s: %d,'%(i, c[i]), end=' ')
        print()

    def print_game(self):
        if self.muted:
            return

        print('price_tokens: ', self.price_tokens.values())
        print('deck size:', len(self._deck))
        self.pprint('market: ', self.market)
        self.pprint('P1 hand: ', self._player1.hand)
        self.pprint('P2 hand: ', self._player2.hand)
        print('P1 camels:', self._player1.camel_count)
        print('P2 camels:', self._player2.camel_count)
        print('P1 tokens: ', self._player1.tokens)
        print('P2 tokens: ', self._player2.tokens)
        print('P1 score:', self._player1.score())
        print('P2 score:', self._player2.score())
        print('Winner is', self.winner)
        print()

    def play_game(self):

        print('----------------- GAME STARTED -------------------')
        self.print_game()

        while self.winner is None:
            if not self.muted:
                print('---------------------', self.player_turn.tag, ' turn', '---------------------')
                self.print_game()

            self = self.switch_player()

            self.game_winner()

        else:
            print('----------------- GAME ENDED -------------------')
            self.print_game()
            # final score includes bonus tokens as well
            print('P1 final score:', self._player1.final_score)
            print('P2 final score:', self._player2.final_score)
            print()
        
        return self.winner


    def switch_player(self):
        self = self.player_turn.do_action(self.winner)

        self.player_turn = next(self._players_gen)
        return self


    def game_winner(self):
        # End game if 3 resources are sold completely
        # Or if market goes less than 5
        if len(['empty' for i in self.price_tokens.values() if not i]) >= 3 or (sum(self.market.values()) < 5):
            self._player1.final_score = self._player1.score()
            self._player2.final_score = self._player2.score()

            if self._player1.camel_count > self._player2.camel_count:
                self._player1.final_score += 5
            elif self._player1.camel_count < self._player2.camel_count:
                self._player2.final_score += 5

            if self._player1.final_score > self._player2.final_score:
                self.winner = self._player1.tag
            elif self._player1.final_score < self._player2.final_score:
                self.winner = self._player2.tag
            else:
                self.winner = self._player2.tag #TODO tie breaker
        return self.winner



