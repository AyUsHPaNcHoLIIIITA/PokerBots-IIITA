'''
This file contains the base class that you should implement for your pokerbot.
'''


class Bot():
    '''
    The base class for a pokerbot.
    '''

    def handle_new_round(self, game_state, round_state, active):
        '''
        Called when a new round starts. Called NUM_ROUNDS times.

        Arguments:

        Returns:
        Nothing.
        '''
        raise NotImplementedError('handle_new_round')

    def handle_round_over(self, game_state, terminal_state, active):
        '''
        Called when a round ends. Called NUM_ROUNDS times.

        Arguments:

        Returns:
        Nothing.
        '''
        raise NotImplementedError('handle_round_over')

    def get_action(self, game_state, round_state, active):
        '''
        Where the magic happens - your code should implement this function.
        Called any time the engine needs an action from your bot.

        Arguments:

        Returns:
        Your action.
        '''
        raise NotImplementedError('get_action')
