from scripts.utils import instruments
import pandas as pd
from ortools.sat.python.cp_model import CpModel, CpSolver

class ScheduleBuilder: 
    def __init__(self, data: pd.DataFrame, n: int):
        self.data = data 
        self.parse_data()
    
    def parse_data(self):
        # parse into availability, instruments, and frequency tables 
        self.availability = self.data[['name', 'w1', 'w2', 'w3', 'w4', 'w5', 'w6', 'w7', 'w8', 'w9', 'w10']]
        self.instruments = self.data[['name'] + instruments]
        self.frequencies = self.data[['name', 'num_weeks']]

        indexed_data = self.data.set_index('name')
        self.availability = self.availability.set_index('name')
        self.instruments = self.instruments.set_index('name')
        self.frequencies = self.frequencies.set_index('name')

        # add a spacing column for each row, calculated based on the number of weeks. 
        num_weeks_to_spacing = {
            1: 4,
            2: 3, 
            3: 2, 
            4: 1
        }

        self.P = list(self.data["name"]) # list of people
        self.frequencies['spacing'] = [num_weeks_to_spacing[indexed_data.loc[person, 'num_weeks']] for person in self.P]
        self.leaders = [person for person in self.P if indexed_data.loc[person, 'is_leader']]

        self.I_all = instruments
        self.I_no_vox = [i for i in instruments if i != "vocals"]
        self.T = list(range(1, 11))

    '''
    Construct model and define variables
    '''
    def build_model(self):
        self.model = CpModel()

        # ---- variables ---- #

        # Creates schedule variables.
        # schedule[(p, w, i)]: person 'p' plays week 'w' on instrument 'o'.
        self.schedule = {}
        for p in self.P:
            for w in self.T:
                for i in self.I_all:
                    self.schedule[(p, w, i)] = self.model.new_bool_var(f"x_{p},week{w},{i}")

        # Create leader variables
        self.leader_assignments = {}
        for p in self.leaders:
            for w in self.T:
                self.leader_assignments[(p, w)] = self.model.new_bool_var(f"l_{p},{w}") 


        self.scheduled_pw = {}
        for p in self.P:
            for w in self.T:
                for i in self.I_all:
                    self.scheduled_pw[(p, w)] = self.model.new_bool_var(f"s_{p},{w}")


        self.set_constraints()
        self.define_penalities_and_objective()


    '''
    Add Constraints to the model

    Current Constraints
        - each person only scheduled on weeks they are available
        - each person only assigned to an instrument they can play
        - at most one non-vocal instrument per person
        - 1-2 guitarists, 1 keys, 3 vocalists per week. Others optional.
        - 1 leader every week. Leader should sing & play
        - more...
    '''
    def set_constraints(self):
        # each person only scheduled on weeks they are available
        # each person only assigned to an instrument they can play
        for p in self.P:
            for w in self.T:
                for i in self.I_all:
                    self.model.add(self.schedule[(p, w, i)] <= min(self.availability.loc[p, f'w{w}'], self.instruments.loc[p, i]))
                
        # at most one instrument (excluding vocals) per person
        for w in self.T:
            for p in self.P:
                self.model.add_at_most_one(self.schedule[(p,w,i)] for i in self.I_no_vox)

        # TODO: keyboard and guitarists may also sing (if they can)
        I_cannot_sing = ["cajon", "strings", "vocals"]
        for w in self.T:
            for p in self.P:
                self.model.add_at_most_one(self.schedule[(p,w,i)] for i in I_cannot_sing)

        # meet instrument requirements: 1-2 guitartists, 1 keys every week, 3 vocalists every week
        for w in self.T:
            # Guitar: allow 1-2 people
            self.model.Add(sum(self.schedule[(p, w, "acoustic_guitar")] for p in self.P) == 1)
            # self.model.Add(sum(self.schedule[(p, w, "Guitar")] for p in self.P) <= 2)
            # Keys: exactly 1
            self.model.add_exactly_one(self.schedule[(p, w, "piano")] for p in self.P)
            # Vocals: exactly 3
            self.model.Add(sum(self.schedule[(p, w, "vocals")] for p in self.P) == 3)

            # Optional Instruments
            self.model.Add(sum(self.schedule[(p, w, "strings")] for p in self.P) <= 1)
            self.model.Add(sum(self.schedule[(p, w, "cajon")] for p in self.P) <= 1)
            self.model.Add(sum(self.schedule[(p, w, "electric_guitar")] for p in self.P) <= 1)


        # 1 leader every week. Leader should be singing.
        for w in self.T:
            self.model.add_exactly_one(self.leader_assignments[(p,w)] for p in self.leaders)
            # Leader must be scheduled to sing
            for p in self.leaders:
                self.model.AddImplication(self.leader_assignments[(p, w)], self.schedule[(p, w, "vocals")])
            
                # TODO: handle both case
                if (self.instruments.loc[p, 'acoustic_guitar']):
                    self.model.AddImplication(self.leader_assignments[(p, w)], self.schedule[(p, w, "acoustic_guitar")])
                elif (self.instruments.loc[p, 'piano']):
                    self.model.AddImplication(self.leader_assignments[(p, w)], self.schedule[(p, w, "piano")])

        # every leader scheduled around twice
        for l in self.leaders:
            self.model.Add(sum(self.leader_assignments[(l, w)] for w in self.T) <= 2)
            self.model.Add(sum(self.leader_assignments[(l, w)] for w in self.T) >= 1)

        # add a variable to easily track if a person is scheduled in week i or not
        for p in self.P:
            for w in self.T:
                self.scheduled_pw[(p, w)] = self.model.NewBoolVar(
                    f"scheduled_{p}_{w}"
                )

                self.model.AddMaxEquality(
                    self.scheduled_pw[(p, w)],
                    [self.schedule[(p, w, i)] for i in self.I_all]
                )

    def define_penalities_and_objective(self):
        self.freq_penalties = {}

        for p in self.P:
            desired_num = int(self.frequencies.loc[p, "num_weeks"])

            num_times_scheduled = sum(
                self.scheduled_pw[(p, w)] for w in self.T
            )

            deviation = self.model.NewIntVar(0, len(self.T), f"deviation_{p}")

            # deviation >= |desired_num - num_times_scheduled|
            self.model.Add(deviation >= desired_num - num_times_scheduled)
            self.model.Add(deviation >= num_times_scheduled - desired_num) 

            self.freq_penalties[p] = deviation

        # map from leader -> list of penalties
        self.leader_penalties = {}
        # spread out leaders - ideally leader gap is at least 3 or 4
        lead_gap = 3
        for l in self.leaders:
            for w in range(len(self.T) - lead_gap):
                for d in range(1, lead_gap):
                    # Auxiliary BoolVar = 1 if leader to lead both week w and week w + desired_gap
                    freq_violation = self.model.NewBoolVar(f"leader_violation_{l}_{w}_{w + d}")
                    
                    # Check if person is leading in week w and w + gap
                    scheduled_w = self.leader_assignments[(l, self.T[w])]
                    scheduled_gap = self.leader_assignments[(l, self.T[w + d])] 
                    
                    # Penalty: freq_violation = 1 if both weeks are scheduled
                    self.model.Add(freq_violation >= scheduled_w + scheduled_gap - 1)
                    self.leader_penalties.setdefault(l, []).append(freq_violation)


        self.spacing_penalties = {}
        for p in self.P:
            desired_gap = self.frequencies.loc[p, "spacing"] + 1 # desired spacing in weeks
            for w in range(len(self.T)):
                for d in range(1, desired_gap):
                    if w + d >= len(self.T):
                        continue

                    freq_violation = self.model.NewBoolVar(f"freq_violation_{p}_{w}_{w+d}")

                    self.model.Add(
                        freq_violation >= self.scheduled_pw[(p, self.T[w])] + self.scheduled_pw[(p, self.T[w + d])] - 1
                    )

                    self.spacing_penalties.setdefault(p, []).append(freq_violation)

        optional_instr = ["electric_guitar", "strings", "cajon"]
        self.optional_rewards = []

        for w in self.T:
            for i in optional_instr:
                # number of people playing optional instrument i in week w
                optional_instr_count = self.model.NewIntVar(
                    0, len(self.P), f"opt_count_{i}_week{w}"
                )

                self.model.Add(
                    optional_instr_count == sum(self.schedule[(p, w, i)] for p in self.P)
                )

                self.optional_rewards.append(optional_instr_count)

        freq_weight = 2
        space_weight = 3
        lead_weight = 1 
        optional_weight = 1

        self.model.Minimize(
            freq_weight * sum(self.freq_penalties.values()) 
            + space_weight * sum(sum(self.spacing_penalties[p]) for p in self.P) 
            + lead_weight * sum(sum(self.leader_penalties[l]) for l in self.leaders)
            - optional_weight * sum(self.optional_rewards)
        )

    '''
    Return a list of n solutions
    '''
    def get_solutions(self, n = 1) -> list:
        self.solver = CpSolver()
    
        solutions = []
        for seed in range(n):  # number of schedules you want
            self.solver.parameters.random_seed = seed
            status = self.solver.Solve(self.model)

            if status == 4:  # optimal
                sol = {}
                for w in self.T:
                    sol[w] = {}
                    for i in self.I_all:
                        sol[w][i] = [
                            p for p in self.P
                            if self.solver.Value(self.schedule[(p, w, i)]) == 1
                        ]
                    for l in self.leaders:
                        if self.solver.value(self.leader_assignments[(l, w)]) == 1:
                            sol[w]['Leader'] = l
            
                    
                diagnostics = self.run_diagnostics()
                solutions.append((sol, diagnostics))
                
        return solutions 

    '''
    Given a solution, return diagnostics per person:
        {
            Person: NumWeeksTotal, NumTimesLeading, [list of weeks scheduled], [instruments each time], 
        }
    Also, return the list of penalties
    '''
    def run_diagnostics(self):
        # for each person, count the number of weeks scheduled
        diagnostics = {}

        for p in self.P:
            weeks_scheduled = []
            weeks_leading = []
            assignments = {}

            for w in self.T:
                insts = [
                    i for i in self.I_all
                    if self.solver.Value(self.schedule[(p, w, i)]) == 1
                ]

                if insts != []:
                    weeks_scheduled.append(w)
                    assignments[w] = insts

                if p in self.leaders and self.solver.Value(self.leader_assignments[(p, w)]) == 1:
                    weeks_leading.append(w)

                frequency_violations = self.solver.Value(self.freq_penalties[p])

            total_weeks = len(weeks_scheduled)
            num_weeks_leading = len(weeks_leading)

            # get spacing and leader penalties
            penalties_p = []
            if (p in self.leaders):
                lead_penalties = self.leader_penalties[p]
                for penalty in lead_penalties:
                    penalty_value = self.solver.Value(penalty)
                    if (penalty_value > 0):
                        penalties_p.append(penalty)
            
            space_pens = self.spacing_penalties[p]
            for penalty in space_pens:
                penalty_value = self.solver.Value(penalty)
                if (penalty_value > 0):
                    penalties_p.append(penalty)

            print(p, penalties_p)
            
            instrument_assignments_str = "; ".join(
                f"Week {w}: {', '.join(i_list)}"
                for w, i_list in assignments.items()
            )

            diagnostics[p] = {
                "Total Weeks Scheduled": total_weeks,
                "Number of Weeks Leading ": num_weeks_leading,
                "Weeks Scheduled": weeks_scheduled,
                "Weeks Leading": weeks_leading,
                "Instruments": instrument_assignments_str,
                "Frequency Deviation": frequency_violations
            }


        return diagnostics
    

 
        
