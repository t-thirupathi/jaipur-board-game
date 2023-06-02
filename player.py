import random
from enum import Enum, IntEnum, unique
from itertools import cycle, combinations, product
from collections import Counter
import numpy as np
import copy
import pickle

from jaipur import *

class Player:

    def __init__(self, strategy, tag, game):
        self.tag = tag
        self.strategy = strategy

        self.camel_count = 0

        self.hand = Counter()
        for i in Commodity:
            self.hand[i] = 0

        self.tokens = []
        self.final_score = 0

        self._game = game


    def hand_size(self):
        return sum(self.hand.values())

    def score(self):
        return sum(self.tokens)

    def get_possible_trades(self, give_commodities, take_commodities):
        # print('give commodities', give_commodities)
        # print('take commodities', take_commodities)

        if len(give_commodities) < 2 or len(take_commodities) < 2:
            return []

        give_commodities = sorted(give_commodities)
        take_commodities = sorted(take_commodities)

        possible_trades = []

        for trade_size in range(2, min(len(give_commodities), len(take_commodities)) + 1):
            give_subsets = set(combinations(give_commodities, trade_size))
            take_subsets = set(combinations(take_commodities, trade_size))

            all_combinations = product(give_subsets, take_subsets)

            for give, take in all_combinations:
                if len(set(give).intersection(set(take))) == 0:
                    possible_trades += [(give, take)]

        return possible_trades

    def get_all_actions(self):
        take_commodities = [i for i in self._game.market if self._game.market[i] > 0]
        sell_commodities = [i for i in self.hand if (self.hand[i] > 1) or (not Commodity.is_precious(i) and self.hand[i] > 0)]

        all_actions = []
        if self.hand_size() < 7:
            all_actions += [(Action.TAKE, i) for i in take_commodities]

        for commodity in sell_commodities:
            precious = Commodity.is_precious(commodity)
            for i in range(precious, self.hand[commodity]):
                all_actions += [(Action.SELL, commodity, i + 1)]

        commodities_to_give = []
        for i in self.hand:
            commodities_to_give += [i] * self.hand[i]
        commodities_to_give += [Commodity.CAMEL] * self.camel_count

        commodities_to_take = []
        for i in self._game.market:
            if i != Commodity.CAMEL:
                commodities_to_take += [i] * self._game.market[i]

        possible_trades = self.get_possible_trades(commodities_to_give, commodities_to_take)
        all_actions += [(Action.TRADE, i) for i in possible_trades]

        return all_actions


    def take(self, commodity=None):
        if not self._game.muted:
            print('taking..', commodity)

        if self.hand_size() < 7:
            taken, take_count = self._game.pick_commodity(commodity)
            if taken == Commodity.CAMEL:
                self.camel_count += take_count
            else:
                self.hand[taken] += take_count

    def sell(self, commodity, count):
        if not self._game.muted:
            print('selling..', commodity)

        if commodity is None:
            commodity = self.hand.most_common(1)[0][0]

        if ((not Commodity.is_precious(commodity)) and self.hand[commodity] > 0) or self.hand[commodity] > 1:
            for i in range(count):
                if self._game.price_tokens[commodity]:
                    self.tokens.append(self._game.price_tokens[commodity].pop())

            self.hand[commodity] -= count

            #TODO use tokens pile instead of random 
            if count == 3:
                self.tokens.append(random.randint(1, 4))
            elif count == 4:
                self.tokens.append(random.randint(4, 7))
            elif count >= 5:
                self.tokens.append(random.randint(7, 11))

    def trade(self, give=None, take=None):
        if not self._game.muted:
            print('trading..', (give, take))

        if give == None or take == None:
            return
        
        if len(give) != len(take):
            return 

        if len(give) < 2:
            return 

        if(set(give).intersection(set(take))):
            return

        give = Counter(give)
        take = Counter(take)

        self.hand -= give
        self._game.market += give

        self._game.market -= take
        self.hand += take

        self.camel_count -= give[Commodity.CAMEL]


    def do_action(self, winner):
        action = self.strategy.choose_action(self)
        if action[0] == Action.TAKE:
            self.take(action[1])
        elif action[0] == Action.SELL:
            self.sell(action[1], action[2])
        elif action[0] == Action.TRADE:
            self.trade(action[1][0], action[1][1])

        return self._game


class PlayerStrategy:
    def choose_action(self, player):
        raise NotImplementedError


class RandomPlayerStrategy(PlayerStrategy):
    def choose_action(self, player):
        all_actions = player.get_all_actions()
        return random.choice(all_actions)


class InteractivePlayerStrategy(PlayerStrategy):
    def choose_action(self, player):
        all_actions = player.get_all_actions()
        for i, action in enumerate(all_actions):
            if action[0] == Action.TRADE:
                print(i, action[0], end=' : ')
                for c in action[1][0]:
                    print(c, end=', ')
                print('with', end=' ')
                for c in action[1][1]:
                    print(c, end=', ')
                print()
            elif action[0] == Action.SELL:
                print(i, action[0], ':', action[1], action[2])
            else:
                print(i, action[0], ':', action[1])
        return all_actions[int(input('Choose action..'))]


class BalancedPlayerStrategy(PlayerStrategy):
    def choose_action(self, player):
        actions = ['take_goods', 'take_camels', 'sell_goods']
        available_goods = player._game.market
        available_tokens = player._game.price_tokens
        player_goods = player.hand

        # Calculate the average value of the goods in the market
        goods_values = [good.value for good in available_goods]
        average_value = sum(goods_values) / len(goods_values)

        # Weights for the different actions
        take_goods_weight = 1
        take_camels_weight = 1
        sell_goods_weight = 1

        # If the average value of goods is higher than a threshold, prioritize taking goods
        if average_value > 3:
            take_goods_weight = 2

        # If the player has a good amount of camels, de-prioritize taking camels
        if player.camel_count > 5:
            take_camels_weight = 0.5

        # If the player has a good amount of goods, prioritize selling them
        if len(player_goods) >= 5:
            sell_goods_weight = 2

        # Normalize the weights
        total_weight = take_goods_weight + take_camels_weight + sell_goods_weight
        take_goods_weight /= total_weight
        take_camels_weight /= total_weight
        sell_goods_weight /= total_weight

        # Choose an action based on the weights
        random_value = random.random()
        if random_value < take_goods_weight:
            return 'take_goods'
        elif random_value < take_goods_weight + take_camels_weight:
            return 'take_camels'
        else:
            return 'sell_goods'

