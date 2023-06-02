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

state_values = dict()

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

    def play_game(self, learn, muted=False):
        self.muted = muted

        print('----------------- GAME STARTED -------------------')
        self.print_game()

        while self.winner is None:
            if not self.muted:
                print('---------------------', self.player_turn.tag, ' turn', '---------------------')
                self.print_game()

            self = self.switch_player(learn)

            self.game_winner()

        else:
            print('----------------- GAME ENDED -------------------')
            self.print_game()
            print('P1 final score:', self._player1.final_score)
            print('P2 final score:', self._player2.final_score)
            print()
        
            if learn and isinstance(self._player1, Agent):
                self._player1.learn_state(self._player1.get_state(), self.winner)
      
            if learn and isinstance(self._player2, Agent):
                self._player2.learn_state(self._player2.get_state(), self.winner)

        return self.winner


    def switch_player(self, learn):
        self = self.player_turn.do_action(self.winner, learn)

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


class Player:
    def __init__(self, tag, game):
        self.tag = tag

        self.camel_count = 0

        self.hand = Counter()
        for i in Commodity:
            self.hand[i] = 0

        self.tokens = []
        self.final_score = 0

        self._game = game

        self.prev_state = self.get_state()


    def hand_size(self):
        return sum(self.hand.values())

    def score(self):
        return sum(self.tokens)

    def get_state(self): #TODO
        #return tuple((self.hand_size(), self.camel_count))

        score = self.score() // 5
        deck_size = self._game.deck_size() // 5

        camel = self.camel_count

        # hand = tuple(self.hand.items())
        hand = tuple(self.hand[i] for i in Commodity)
        hand_size = self.hand_size()

        # market_precious = sum([self._game.market[i] for i in Commodity if Commodity.is_precious(i)])
        # market_non_precious = sum([self._game.market[i] for i in Commodity if (not Commodity.is_precious(i)) and (not i == Commodity.CAMEL)])
        # market_camel = sum([self._game.market[i] for i in Commodity if i == Commodity.CAMEL])

        # market = (market_precious, market_non_precious, market_camel)
        
        market = tuple(self._game.market[i] for i in Commodity)

        state = tuple((score, deck_size, hand_size, hand, camel, market))
        return state

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

            if count == 3:
                self.tokens.append(random.randint(1, 4))
            elif count == 4:
                self.tokens.append(random.randint(4, 7))
            elif count >= 5:
                self.tokens.append(random.randint(7, 11))

        # print('after selling...', self.tokens)

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

    def do_action(self, winner, learn=False):
        all_actions = self.get_all_actions()
        action = random.choice(all_actions)

        for i, action in enumerate(all_actions):
            #To make print look less cluttered
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
        action = all_actions[int(input('Choose action..'))]

        if action[0] == Action.TAKE:
            self.take(action[1])
        elif action[0] == Action.SELL:
            self.sell(action[1], action[2])
        elif action[0] == Action.TRADE:
            self.trade(action[1][0], action[1][1])

        return self._game


class Agent(Player):
    def __init__(self, tag, game):
        super().__init__(tag, game)

    def do_action(self, winner, learn):
        if learn:
            self.learn_state(self.get_state(), winner)
        
        if learn:
            epsilon = 0.8
        else:
            epsilon = 1

        p = random.uniform(0, 1)

        if p < epsilon:
            self._game = self.do_optimal_action()

        else:
            super().do_action(winner, learn)

        return self._game

    def do_optimal_action(self):
        opt_self = None
        v = -float('Inf')

        all_actions = self.get_all_actions()
        # print('all_actions')
        # for i in all_actions:
        #     print(i)

        if_equal_divide_by = 1
        for m, c in sorted(all_actions, reverse=False):
            temp_self = copy.deepcopy(self)

            if m == 0:
                temp_self.take(c)

            elif m == 1:
                temp_self.sell(c)

            elif m == 2:
                temp_self.trade(c[0], c[1])

            # print('after making action', m, c)
            # temp_self._game.print_game()
            # print()
            
            temp_state = self.get_state()
            v_temp = self.calc_value(temp_state)

            # Encourage exploration
            if v_temp is None:
                v_temp = 1

            if v_temp > v:
                opt_self = copy.deepcopy(temp_self)
                v = v_temp

            elif v_temp == v:
                opt_self = copy.deepcopy(temp_self)
                # # gives uniform prob distribution for all equal value states
                # update_prob = 1.0 / if_equal_divide_by
                # p = random.uniform(0, 1)
                # if p > (1 - update_prob):
                #     opt_self = copy.deepcopy(temp_self)
                # if_equal_divide_by += 1

        self = copy.deepcopy(opt_self)

        # print('Optimal self')
        # opt_self._game.print_game()
        # print()

        # print('After making optimal action')
        # self._game.print_game()

        return self._game


    def calc_value(self, state):
        global state_values
        if state in state_values.keys():
            return state_values[state]

    def learn_state(self, state, winner):
        global state_values
        # if winner is not None:
        #     state_values[state] = self.reward(winner)

        if self.prev_state in state_values.keys():
            v_s = state_values[self.prev_state]
        else:
            v_s = int(0)

        R = self.reward(winner)

        if state in state_values.keys() and winner is None:
            v_s_tag = state_values[state]
        else:
            v_s_tag = int(0)

        state_values[self.prev_state] = v_s + 0.5 * (R + v_s_tag - v_s)

        self.prev_state = state

    def reward(self, winner):
        if winner is self.tag:
            R = 1
        elif winner is None:
            R = 0
        else:
            R = -1
        return R



def load_values():
    global state_values
    try:
        f = open('state_values.pickle', 'rb')
        state_values = pickle.load(f)
    except:
        state_values = dict()

def save_values():
    global state_values
    f = open('state_values.pickle', 'wb')
    try:
        os.reaction(f)
    except:
        pass

    pickle.dump(state_values, f)


def play_to_learn(episodes, muted=True):
    load_values()
    print(len(state_values))

    for i in range(episodes):
        print('Episode', i)

        game = Jaipur(Agent, Player)
        game.play_game(learn=True, muted=muted)

        game = Jaipur(Player, Agent)
        game.play_game(learn=True, muted=muted)

        if i % 1000 == 0:
            save_values()

    save_values()
    
    print(len(state_values))

    count = 0
    for i in state_values:
        if state_values[i] not in (-0.5, 0, 0.5):
            print(i, state_values[i])
            count += 1

    print(count)

    # print(state_values)

def test(n=100):
    load_values()

    print('----------------------------------------------------------------- Agent vs Agent')
    ava_p1_wins = 0
    for i in range(n):
        game = Jaipur(Agent, Agent)
        winner = game.play_game(learn=False, muted=True)
        if winner == 'P1':
            ava_p1_wins += 1

    print('----------------------------------------------------------------- Agent vs Player')
    avp_p1_wins = 0
    for i in range(n):
        game = Jaipur(Agent, Player)
        winner = game.play_game(learn=False, muted=True)
        if winner == 'P1':
            avp_p1_wins += 1

    print('----------------------------------------------------------------- Player vs Agent')
    pva_p1_wins = 0
    for i in range(n):
        game = Jaipur(Player, Agent)
        winner = game.play_game(learn=False, muted=True)
        if winner == 'P1':
            pva_p1_wins += 1

    print('----------------------------------------------------------------- Player vs Player')
    pvp_p1_wins = 0
    for i in range(n):
        game = Jaipur(Player, Player)
        winner = game.play_game(learn=False, muted=True)
        if winner == 'P1':
            pvp_p1_wins += 1


    print('----------------------------------------------------------------- Result')

    print('----------------------------------------------------------------- Agent vs Agent')
    print('Total:', n)
    print('P1:', ava_p1_wins)
    print('P2:', n - ava_p1_wins)

    print('----------------------------------------------------------------- Agent vs Player')
    print('Total:', n)
    print('P1:', avp_p1_wins)
    print('P2:', n - avp_p1_wins)

    print('----------------------------------------------------------------- Player vs Agent')
    print('Total:', n)
    print('P1:', pva_p1_wins)
    print('P2:', n - pva_p1_wins)


    print('----------------------------------------------------------------- Player vs Player')
    print('Total:', n)
    print('P1:', pvp_p1_wins)
    print('P2:', n - pvp_p1_wins)


if __name__ == "__main__":
    play_to_learn(100000, muted=True)

    game = Jaipur(Player, Agent)
    game.play_game(learn=False, muted=False)

    test(100)


