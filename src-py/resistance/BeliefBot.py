from agent import Agent
import random


class BeliefBot(Agent):        
    def __init__(self, name='BeliefBot'):
        '''
        Initialises the agent.
        Nothing to do here.
        '''
        self.name = name

    def new_game(self, number_of_players, player_number, spy_list):
        '''
        initialises variables and data structures to be used 
        '''
        # variables for the game type
        self.m_size = self.mission_sizes[number_of_players]
        self.n_spy = self.spy_count[number_of_players]
        self.n_fails = self.fails_required[number_of_players]

        self.id = player_number
        self.spies = spy_list
        self.N = number_of_players
        self.n_res = self.N - self.n_spy

        # stores the suspicious value of each player and sets this agent's value to 0
        self.player_sus = [self.n_spy / (self.N - 1) for _ in range(number_of_players)]
        self.player_sus[self.id] = 0

        # stores the mission's and rounds (in each mission) completed
        self.M = 0
        self.R = 0

        # stores the total number of missions succeeded and failed
        self.successes = 0
        self.failures = 0

        # True if agent is a spy
        self.spy = self.id in self.spies

        # stores the set of successful and unsuccesful teams
        self.good_teams = set()
        self.bad_teams = set()

        # constants used for giving rewards and penalties
        self.PEN_THRESH = 0.9
        self.PENALTY = 0.05
        self.REWARD = -0.03
        self.SPY_THRESH = 0.7

        # initialise the fail rate
        self.update_fail_rate()


    def propose_mission(self, team_size, betrayals_required = 1):
        '''
        if spy, then select enough spies with the least probability to be able to fail the mission
        selects the players with the least probability of being a spy
        ''' 
        team = []
        spy_count = 0
        # add itself if team size is the same as number of resistance
        if self.n_res == team_size:
            team.append(self.id)
            spy_count += 1

        # get the rank of the agents by their suspicious value from lowest to highest
        spies_guess = self.get_spy_chance_order()

        # pick the spies with the lowest suspicious value
        if self.spy:
            counter = 0
            while spy_count < betrayals_required:
                if not spies_guess[counter] in team and spies_guess[counter] in self.spies:
                    team.append(spies_guess[counter])
                    spy_count += 1
                counter += 1

        # pick the rest of the team with the lowest suspicious values
        for i in spies_guess:
            if len(team) == team_size:
                break
            if not i in team:
                team.append(i)

        return team
  

    def vote(self, mission, proposer):
        '''
        set of conditions to go through to determine if player should vote approve or reject
        '''
        if len(mission) == self.n_res and not self.id in mission:
            return False

        # if not enough spies to fail the mission
        if self.spy:
            n_spies = 0
            for i in self.spies:
                if i in mission:
                    n_spies += 1
            if n_spies < self.n_fails[self.M]:
                return False 

        # if team has failed previously
        if self.has_team_failed(mission):
            return False

        # if the team has a high chance of containing spies
        if self.can_mission_fail(mission):
            return False

        # if the proposer is a potential spy
        if self.player_sus[proposer] >= self.SPY_THRESH:
            return False

        return True


    def vote_outcome(self, mission, proposer, votes):
        '''
        gives agents rewards or penalties based on their votes
        '''

        # if the team has previously failed, penalise approvers and proposer. Reward rejectors
        if self.has_team_failed(mission):
            for i in range(self.N):
                if i in votes:
                    if self.player_sus[i] < self.PEN_THRESH:
                        self.player_sus[i] += self.PENALTY
                else:
                    if self.player_sus[i] > 1 - self.PEN_THRESH:
                        self.player_sus[i] += self.REWARD
                    
            if self.player_sus[proposer] < self.PEN_THRESH:
                    self.player_sus[proposer] += self.PENALTY
        
        # if the team has previously succeeded, reward approvers and proposer. penalise rejectors
        if self.has_team_succeeded(mission):
            for i in range(self.N):
                if i not in votes:
                    if self.player_sus[i] < self.PEN_THRESH:
                        self.player_sus[i] += self.PENALTY
                else:
                    if self.player_sus[i] > 1 - self.PEN_THRESH:
                        self.player_sus[i] += self.REWARD

            if self.player_sus[proposer] < self.PEN_THRESH:
                self.player_sus[proposer] += self.REWARD

        # if the team has high chance of failure, penalise approvers and proposer. reward rejectors
        if self.can_mission_fail(mission):
            for i in range(self.N):
                if i in votes:
                    if self.player_sus[i] < self.PEN_THRESH:
                        self.player_sus[i] += self.PENALTY
                else:
                    if self.player_sus[i] > 1 - self.PEN_THRESH:
                        self.player_sus[i] += self.REWARD

            if self.player_sus[proposer] < self.PEN_THRESH:
                self.player_sus[proposer] += self.PENALTY
            
        

    def betray(self, mission, proposer):
        '''
        a spy will betray according to its failrate
        '''
        if self.spy:
            if self.failures == 2:
                return True
            return random.random() < self.fail_rate

    def mission_outcome(self, mission, proposer, betrayals, mission_success):
        '''
        Applies bayes' theorem to update the probability of the players in the mission being a spy
        Updates the set of successful and unsuccessful teams
        '''

        # copy of the current suspicious values as they will be overwritten
        current_sus = self.player_sus.copy()

        # probability of failing with betrayals number of fails 
        pB = self.mission_fail_chance(mission, current_sus, betrayals)

        # avoid division by 0, can be caused by a spy
        if pB <= 0:
            pB = 0.5

        # calculate probability of failing with betrayals number of fails given the player is a spy
        # update their suspicious value    
        for i in range(len(mission)):
            pBA = self.mission_fail_given_spy(mission, current_sus, i, betrayals)
            pA = current_sus[mission[i]]

            pAB = (pBA * pA) / pB
            self.player_sus[mission[i]] = pAB
        
        # add team to good_teams or bad_teams list based on if the mission succeeded
        self.update_teams(mission, mission_success)

        # penalise or reward the proposer based on if the mission succeeded
        if not mission_success:
            if self.SPY_THRESH < self.player_sus[proposer] < self.PEN_THRESH:
                self.player_sus[proposer] += 0.5
        else:
            if self.player_sus[proposer] > 1 - self.PEN_THRESH:
                self.player_sus[proposer] += self.REWARD


    def round_outcome(self, rounds_complete, missions_failed):
        '''
        updates game state variables
        '''
        self.M = rounds_complete
        self.failures = missions_failed
        self.successes = self.M - self.failures
    
    def game_outcome(self, spies_win, spies):
        '''
        unused
        '''
        #nothing to do here
        pass

    def get_spy_chance_order(self):
        '''
        takes player_sus and returns a list which orders the player id's 
        from least probability of being spy to most probability
        e.g. [0, 0.5, 0.1, 1, 0.8] -> [0, 2, 1, 4, 3]
        '''
        return sorted(range(len(self.player_sus)), key=lambda k: self.player_sus[k])

    def get_permutations(self, mission_size, betrayals):
        '''
        returns the different permuations of mission outcomes for a given number of fails
        '''
        permutations = []
        for p in range(2**mission_size):
            pb = "{0:b}".format(p).zfill(mission_size)
            if pb.count('1') == betrayals:
                permutations.append(pb)
        
        return permutations

    def update_teams(self, mission, mission_success):
        '''
        stores the different combination of teams that have succeeded or failed
        '''
        good_teams_copy = self.good_teams.copy()

        # if the team isn't already in the bad teams list, add it to the good teams lists
        if mission_success:
            if not tuple(sorted(mission)) in self.bad_teams:
                is_super = False
                for bt in self.bad_teams:
                    if set(mission).issuperset(set(bt)):
                        is_super = True
                if not is_super:
                    self.good_teams.add(tuple(sorted(mission)))
        else:
            # if the team was in the good teams list, remove it and add it to bad teams
            for gt in good_teams_copy:
                if set(gt).issuperset(set(mission)) or set(gt) == set(mission):
                    self.good_teams.remove(gt)

            self.bad_teams.add(tuple(sorted(mission)))


    def update_fail_rate(self):
        '''
        update the spy fail rate variables
        fail rate is determined by the number of fails required 
        and the number of missions remaining minus 1
        this is the minimum probability needed for spies to win 
        if one mission succeeds from the current game state
        '''

        if self.M < 4:
            self.fail_rate = (3-self.failures) / (5-self.M-1)
        
        # fail rate will be 0 if spies have won 
        # fail rate can be arbitrarily set as this won't affect game outcome
        if self.fail_rate <= 0:
            self.fail_rate = 0.5


    def mission_fail_chance(self, mission, player_sus, betrayals):
        '''
        calculates the probability of a mission failing with a specific number of fails
        '''
        p_fail = 0
        permutations = self.get_permutations(len(mission), betrayals)
        
        # calculate the probability of each permutation occuring. 
        # 0 indicates the player succeeded the mission, 1 indicates the player failed the mission
        for p in permutations:
            probability = 1
            for i in range(len(p)):
                if p[i] == '1':
                    probability *= (player_sus[mission[i]] * self.fail_rate)      
                else:
                    probability *= (player_sus[mission[i]] * (1 - self.fail_rate) + (1 - player_sus[mission[i]])) 
            
            p_fail += probability

        return p_fail


    def mission_fail_given_spy(self, mission, player_sus, player_index, betrayals):
        '''
        calculates the probability of the mission failing 
        with a specific number of fails given player is a spy
        '''
        p_fail = 0
        permutations = self.get_permutations(len(mission), betrayals)

        for p in permutations:
            probability = 1
            for i in range(len(p)):
                if i == player_index:
                    if p[i] == '1':
                        probability *= self.fail_rate
                    else:
                        probability *= (1 - self.fail_rate)
                else:
                    if p[i] == '1':
                        probability *= (player_sus[mission[i]] * self.fail_rate)
                    else:
                        probability *= (player_sus[mission[i]] * (1 - self.fail_rate) +  (1 - player_sus[mission[i]]))

            p_fail += probability
        
        return p_fail

    def has_team_failed(self, mission):
        '''
        checks if the team has previously failed a mission
        '''
        if tuple(sorted(mission)) in self.bad_teams:
            return True

        for bt in self.bad_teams:
            if set(mission).issuperset(set(bt)):
                return True
        return False

    def has_team_succeeded(self, mission):
        '''
        checks if the mission has only succeeded missions
        '''
        if tuple(sorted(mission)) in self.good_teams:
            return True

        for gt in self.good_teams:
            if set(mission).issuperset(set(gt)):
                return True
        return False 

    def can_mission_fail(self, mission):
        '''
        returns True if there are enough suspected spies to fail the mission
        '''
        spy_count = [i for i in mission if self.player_sus[i] >= self.SPY_THRESH]
        return len(spy_count) >= self.n_fails[self.M]


