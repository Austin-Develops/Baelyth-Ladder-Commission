import elo_calc.elo as elo


# uses elo
# There are tiers, and actual points. There is a base tier point added depending on tier difference
# then there is an additional difference points that are added based on the actual point values
# If they are in the same tier, then 

elo.Elo(20, int, 0, 100).make_as_global()

def determine_rank(points):
    cutoffs = [-1, 150, 300, 450, 600, 800]
    names = ['F', 'D', 'C', 'B', 'A', 'S']
    ind = 5
    while points < cutoffs[ind]:
        ind -= 1
    return ind, names[ind]

def determine_tier_points(points1, points2, r1_win):
    r1, _ = determine_rank(points1)
    r2, _ = determine_rank(points2)
    difference = abs(r1 - r2)
    delta_higher_point_set = (max(0, 15 - 5 * difference), -10 - 2 * difference) # Win vs Lose
    delta_lower_point_set = (15 + 5 * difference, min(0, -10 + 4 * difference))
    point_change_sets = [delta_higher_point_set, delta_lower_point_set]
    if r1 < r2:
        point_change_sets.reverse()
    
    mark_ind = int(not r1_win) # 0 if r1 wins which is the r1 index
    return (point_change_sets[0][mark_ind], point_change_sets[1][(mark_ind + 1) % 2])

def play_game(initial_points1, initial_points2, p1_win):
    delta_tier_points = determine_tier_points(initial_points1, initial_points2, p1_win)
    p1 = elo.Rating(initial_points1)
    p2 = elo.Rating(initial_points2)
    if p1_win:
        new_p1, new_p2 = elo.rate_1vs1(p1, p2)
    else:
        new_p2, new_p1 = elo.rate_1vs1(p2, p1)
    delta_volatile_points = [new_p1 - initial_points1, new_p2 - initial_points2]
    tier_volatile_deltas = [list(i) for i in zip(delta_tier_points, delta_volatile_points)] 
    delta_total = [sum(tier_volatile_deltas[0]), sum(tier_volatile_deltas[1])]
    if initial_points1 + delta_total[0] < 0:
        delta_total[0] = -initial_points1
        # print(f'{initial_points1 = }')
        new_tp = max(tier_volatile_deltas[0][0], delta_total[0])
        # print(f'{tier_volatile_deltas[0][0]} vs {delta_total[0]} -> {new_tp}')
        tier_volatile_deltas[0][0] = new_tp
        new_vol = min(delta_total[0] - new_tp, 0)
        # print(f'{delta_total[0]} - {new_tp} vs 0 -> {new_vol}')
        tier_volatile_deltas[0][1] = new_vol
    
    if initial_points2 + delta_total[1] < 0:
        delta_total[1] = -initial_points2
        # print(f'{initial_points1 = }')
        new_tp = max(tier_volatile_deltas[1][0], delta_total[1])
        # print(f'{tier_volatile_deltas[0][0]} vs {delta_total[0]} -> {new_tp}')
        tier_volatile_deltas[1][0] = new_tp
        new_vol = min(delta_total[1] - new_tp, 0)
        # print(f'{delta_total[0]} - {new_tp} vs 0 -> {new_vol}')
        tier_volatile_deltas[1][1] = new_vol
        
        
    return tier_volatile_deltas, delta_total
