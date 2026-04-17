'''
Aces Bot — PokerBots IIITA Submission
=======================================
Heads-up Bounty Hold'em bot.

Strategy:
Position-aware range chart (BTN open-ranges, BB defense)
EV when holding bounty rank in hand/board
'''

import random
import time
from itertools import combinations

from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot


# ── Card utilities ────────────────────────────────────────────────────────────
RANKS = '23456789TJQKA'
SUITS = 'shdc'

    return RANK_VAL[c[0]]

    return SUITS.index(c[1])

def hand_to_ints(cards):
    """Convert ['As','Kd'] → [int, int] for fast MC."""
    return [card_rank(c) * 4 + card_suit(c) for c in cards]

    return RANKS[n // 4] + SUITS[n % 4]


# ── Fast 5-card hand evaluator (integer encoding) ─────────────────────────────
def evaluate_5(cards):
    """Return (category, tiebreaker) — higher is better. Category 0–8."""
    ranks = sorted([c // 4 for c in cards], reverse=True)
    suits = [c % 4 for c in cards]
    flush  = len(set(suits)) == 1
    straight = (ranks[0] - ranks[4] == 4 and len(set(ranks)) == 5) or ranks == [12,3,2,1,0]
# wheel
        ranks = [3,2,1,0,-1]

    counts = sorted([(ranks.count(r), r) for r in set(ranks)], reverse=True)
    groups = [c[0] for c in counts]

   return (7, [counts[0][1], counts[1][1]])
    if groups[:2] == [3,2]:return (6, [counts[0][1], counts[1][1]])
            return (5, ranks)
         return (4, ranks)
   return (3, [counts[0][1]] + [counts[1][1], counts[2][1]])
    if groups[:2] == [2,2]:return (2, [counts[0][1], counts[1][1], counts[2][1]])
   return (1, [counts[0][1]] + [counts[1][1], counts[2][1], counts[3][1]])
    return (0, ranks)

def best_hand_7(cards7):
    return max(evaluate_5(list(c)) for c in combinations(cards7, 5))


# ── Monte Carlo equity ────────────────────────────────────────────────────────
def calc_equity(my_cards_str, board_str, n_sims=300):
    """Estimate win probability via Monte Carlo. Returns float 0–1."""
    my_ints   = hand_to_ints(my_cards_str)
    board_ints= hand_to_ints(board_str)
    used      = set(my_ints + board_ints)

    deck = [i for i in range(52) if i not in used]
    need = 5 - len(board_ints)   # cards still to come

    wins = 0
    for _ in range(n_sims):
        sample = random.sample(deck, need + 2)   # fill board + 2 opp cards
        full_board = board_ints + sample[:need]
        opp_cards  = sample[need:]

        my_score  = best_hand_7(my_ints + full_board)
        opp_score = best_hand_7(opp_cards + full_board)
        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            wins += 0.5

    return wins / n_sims


# ── Preflop range (heads-up adjusted) ─────────────────────────────────────────
# We use a tier system; HU ranges are very wide.
def preflop_tier_hu(high_r, low_r, suited):
    """
    Return tier 1-5 for HU play.
    1 = raise any position, 5 = marginal / fold facing raise
    """
    pair = high_r == low_r
    gap  = high_r - low_r

    # Pairs
    if pair:
return 1   # TT+
return 2   # 66-99
        return 3                     # 22-55

    # Aces
    if high_r == 12:
return 1   # AQ+
 return 2   # AT+
        return 3 if suited else 4   # Axs / Axo

    # Broadway
return 2   # KQ,KJ,QJ,JT

    # Suited connectors / gappers

    # Any connected card HU

    return 5


# ── Opponent stats tracker ────────────────────────────────────────────────────
class OppModel:
    def __init__(self):
        self.hands = 0
        self.vpip  = 0    # voluntarily entered pot preflop
        self.pfr   = 0    # preflop raised
        self.bets   = 0   # postflop bets/raises
        self.calls  = 0   # postflop calls
        self.fold_cb= 0   # folded to our postflop bet
        self.cb_seen= 0   # saw our postflop bet

return self.vpip / max(self.hands, 1)
 return self.pfr  / max(self.hands, 1)
       return self.bets  / max(self.calls, 1)
      return self.fold_cb / max(self.cb_seen, 1)

 return self.vpip_rate() > 0.55

    def fold_equity(self):
        """Estimated probability opponent folds to our bet."""
        base = self.fcb()
# no data — assume 45%
            return 0.45
        return max(0.10, min(0.85, base))


# ── Main Bot ──────────────────────────────────────────────────────────────────
class Player(Bot):

    def __init__(self):
        self.opp   = OppModel()
        self.round  = 0

        # Per-round state
        self._my_preflop_action = None   # 'raise' or 'call' or 'check'
        self._bet_this_round    = False  # did we bet postflop this round?
        self._opp_preflop_raised = False

    # ── Round bookkeeping ──────────────────────────────────────────────────────
    def handle_new_round(self, game_state, round_state, active):
        self.round += 1
        self.opp.hands += 1
        self._my_preflop_action  = None
        self._bet_this_round     = False
        self._opp_preflop_raised = False

    def handle_round_over(self, game_state, terminal_state, active):
        prev = terminal_state.previous_state
        # Record if opponent voluntarily played / raised preflop
        # (approximated by their pip > BB at end of preflop)
        # We record this in get_action via flags

    # ── Core decision ─────────────────────────────────────────────────────────
    def get_action(self, game_state, round_state, active):
        legal   = round_state.legal_actions()
        street  = round_state.street   # 0=preflop, 3=flop, 4=turn, 5=river
        my_cards   = round_state.hands[active]
        board_cards= round_state.deck[:street]
        my_pip  = round_state.pips[active]
        opp_pip = round_state.pips[1-active]
        my_stack= round_state.stacks[active]
        opp_stack = round_state.stacks[1-active]
        my_bounty  = round_state.bounties[active]
        continue_cost = opp_pip - my_pip
        pot = my_pip + opp_pip   # chips already committed

        # Time guard — if < 5 seconds left, play simple
        if game_state.game_clock < 5.0:
            return self._emergency_action(legal, continue_cost, pot, my_stack)

        bounty_hit = self._check_bounty(my_bounty, my_cards, board_cards)

        # ── PREFLOP ───────────────────────────────────────────────────────────
        if street == 0:
            return self._preflop(legal, my_cards, my_pip, opp_pip,
                                 my_stack, continue_cost, pot,
                                 active, bounty_hit, game_state)

        # ── POSTFLOP ──────────────────────────────────────────────────────────
        return self._postflop(legal, my_cards, board_cards,
                              my_pip, opp_pip, my_stack, opp_stack,
                              continue_cost, pot, street,
                              active, bounty_hit, game_state)

    # ── Preflop logic ─────────────────────────────────────────────────────────
    def _preflop(self, legal, my_cards, my_pip, opp_pip,
                 my_stack, continue_cost, pot, active, bounty_hit, game_state):

        r0 = card_rank(my_cards[0])
        r1 = card_rank(my_cards[1])
        hi, lo = max(r0,r1), min(r0,r1)
        suited = card_rank(my_cards[0]) != card_rank(my_cards[1]) and \
                 my_cards[0][1] == my_cards[1][1]
        suited = my_cards[0][1] == my_cards[1][1]

        tier = preflop_tier_hu(hi, lo, suited)
        is_btn = (active == 0)   # BTN=SB acts first preflop in HU

        # SPR
        spr = my_stack / max(pot, 1)

        min_raise, max_raise = (0, 0)
        if RaiseAction in legal:
            min_raise, max_raise = round_state_bounds_safe(legal, opp_pip, my_pip, my_stack)

        # ── Facing a raise ────────────────────────────────────────────────────
        if continue_cost > 0:
            self._opp_preflop_raised = True
            self.opp.pfr += 1
            self.opp.vpip += 1

            call_cost_frac = continue_cost / max(my_stack, 1)

 # premium: 3-bet or jam
                if RaiseAction in legal:
                    amount = min(int(opp_pip * 3), max_raise)
                    self._my_preflop_action = 'raise'
                    return RaiseAction(max(amount, min_raise))
                self._my_preflop_action = 'call'
                return CallAction()

 # speculative, cheap
                self._my_preflop_action = 'call'
                return CallAction()

            if tier <= 4 and call_cost_frac < 0.12:
                self._my_preflop_action = 'call'
                return CallAction()

            # Fold marginal / expensive call
            if FoldAction in legal:
                return FoldAction()
            return CallAction()

        # ── No raise faced ────────────────────────────────────────────────────
 # BTN: open-raise wide
            if tier <= 4 or bounty_hit:
                if RaiseAction in legal:
                    open_size = min(max(BIG_BLIND * 2, int(pot * 2.5)), max_raise)
                    self._my_preflop_action = 'raise'
                    return RaiseAction(max(open_size, min_raise))
            if RaiseAction in legal and random.random() < 0.3:
                open_size = min(BIG_BLIND * 2, max_raise)
                return RaiseAction(max(open_size, min_raise))
            if CheckAction in legal:
                return CheckAction()
            return CallAction()
 # BB: check or raise good hands
            if tier <= 2 and RaiseAction in legal:
                squeeze = min(int(pot * 3), max_raise)
                self._my_preflop_action = 'raise'
                return RaiseAction(max(squeeze, min_raise))
            if CheckAction in legal:
                self._my_preflop_action = 'check'
                return CheckAction()
            return CallAction()

    # ── Postflop logic ────────────────────────────────────────────────────────
    def _postflop(self, legal, my_cards, board_cards,
                  my_pip, opp_pip, my_stack, opp_stack,
                  continue_cost, pot, street, active, bounty_hit, game_state):

        # Determine sim budget based on remaining time
        sims = 300
        if game_state.game_clock < 15:
            sims = 150
        elif game_state.game_clock < 30:
            sims = 200

        equity = calc_equity(my_cards, board_cards, n_sims=sims)

        if bounty_hit:
            equity = min(equity + 0.08, 0.99)

        # Pot odds required to call
        total_pot = pot + continue_cost
        pot_odds  = continue_cost / max(total_pot, 1) if continue_cost > 0 else 0

        # Opponent model
        fold_eq = self.opp.fold_equity()
        opp_passive  = self.opp.is_passive()
        opp_loose    = self.opp.is_loose()

        # SPR
        eff_stack = min(my_stack, opp_stack)
        spr = eff_stack / max(pot, 1)

        # ── Raise/Bet bounds ──────────────────────────────────────────────────
        can_raise = RaiseAction in legal
        min_raise, max_raise = (0, 0)
        if can_raise:
            min_raise, max_raise = round_state_bounds_safe(legal, opp_pip, my_pip, my_stack)

        # ── Value threshold ───────────────────────────────────────────────────
        # Adjust for opponent model
        val_thresh = 0.56
 val_thresh = 0.48   # value bet thinner vs fish
val_thresh = 0.60   # be cautious vs aggro

        is_value = equity >= val_thresh

        # ── Semi-bluff / bluff ────────────────────────────────────────────────
        # Only bluff on flop/turn, never on river vs passive opponents
        is_bluff = False
        if not is_value and can_raise and street < 5:
            needed_fold_eq = continue_cost / max(pot + continue_cost, 1)
            if fold_eq > 0.52 and not (opp_loose and opp_passive):
                is_bluff = True

        # ── Against a bet (continue_cost > 0) ────────────────────────────────
        if continue_cost > 0:
            # Record opponent postflop aggression
            self.opp.bets += 1

            # If we already bet (they're raising us), track
            if self._bet_this_round:
                self.opp.cb_seen += 1

            ev_call = equity * (pot + continue_cost) - (1 - equity) * continue_cost

            # Value raise
            if is_value and can_raise and equity > 0.68:
                bet = self._size_raise(pot, equity, min_raise, max_raise, my_stack, street, spr)
                self._bet_this_round = True
                return RaiseAction(bet)

            # Call with positive EV or pot odds justified
            if equity > pot_odds + 0.04 or ev_call > 0:
                self.opp.calls += 1
                return CallAction()

            # Fold
            if FoldAction in legal:
                if self._bet_this_round:
                    self.opp.fold_cb += 1   # we bet, they raised, we fold — unusual but track
                return FoldAction()
            return CallAction()

        # ── No bet to us (check or first to act) ─────────────────────────────
        if is_value and can_raise:
            bet = self._size_bet(pot, equity, min_raise, max_raise, my_stack, street, spr)
            self._bet_this_round = True
            return RaiseAction(bet)

        if is_bluff and can_raise:
            # Polar bluff size
            bet = self._size_bet(pot, 0.3, min_raise, max_raise, my_stack, street, spr)
            self._bet_this_round = True
            return RaiseAction(bet)

        # Check back
        if CheckAction in legal:
            return CheckAction()

        return CallAction()

    # ── Bet sizing ────────────────────────────────────────────────────────────
    def _size_bet(self, pot, equity, min_raise, max_raise, stack, street, spr):
        """Compute a good bet size when we're first to bet."""
        if equity > 0.80:
            frac = 0.85   # pot-size or overbet with nuts
        elif equity > 0.65:
            frac = 0.60   # 2/3 pot
        else:
            frac = 0.40   # probe bet / bluff

        if street == 5 and equity > 0.85:
            frac = 1.10

        if spr < 2 and equity > 0.60:
            return max_raise

        raw = int(pot * frac)
        return max(min_raise, min(raw, max_raise))

    def _size_raise(self, pot, equity, min_raise, max_raise, stack, street, spr):
        """Raise size when facing a bet."""
        if spr < 2:
            return max_raise   # jam
        if equity > 0.80:
            raw = int(pot * 2.5)
        else:
            raw = int(pot * 1.8)
        return max(min_raise, min(raw, max_raise))

    # ── Bounty check ─────────────────────────────────────────────────────────
    def _check_bounty(self, bounty_rank, my_cards, board_cards):
        """True if our bounty rank appears in hole or board."""
        if not bounty_rank:
            return False
        all_cards = my_cards + board_cards
        return any(c[0] == bounty_rank for c in all_cards)

    # ── Emergency fallback (clock < 5s) ───────────────────────────────────────
    def _emergency_action(self, legal, continue_cost, pot, my_stack):
        if continue_cost == 0:
            if CheckAction in legal:
                return CheckAction()
        # Pot odds > 33%? Call
        if continue_cost / max(pot + continue_cost, 1) < 0.33:
            return CallAction()
        if FoldAction in legal:
            return FoldAction()
        return CallAction()


def round_state_bounds_safe(legal, opp_pip, my_pip, my_stack):
    """Return (min_raise_total, max_raise_total) from legal actions context."""
    # In the skeleton, raise_bounds() is on RoundState — we reconstruct manually
    # min raise = at least call + last raise size (≥ BB), at most all-in
    continue_cost = max(0, opp_pip - my_pip)
    max_contrib   = min(my_stack, my_stack)   # can't bet more than we have
    min_contrib   = min(max_contrib, continue_cost + max(continue_cost, BIG_BLIND))
    min_r = my_pip + min_contrib
    max_r = my_pip + max_contrib
    return (min_r, max_r)


if __name__ == '__main__':
    run_bot(Player(), parse_args())
