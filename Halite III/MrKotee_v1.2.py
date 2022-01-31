#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction, Position

# This library allows you to generate random numbers.
import random

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("MrKotee_v1.2")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))
logging.info("map size h={}, w={}".format(game.game_map.height, game.game_map.width))


def correct_coordinates(game_map, pos):
    _pos = pos
    if pos.x < 0:
        _pos = Position(game_map.width - pos.x, pos.y)
    elif pos.x == game_map.width:
        _pos = Position(0, pos.y)
    if pos.y < 0:
        _pos = Position(pos.x, game_map.height - pos.y)
    elif pos.y == game_map.height:
        _pos = Position(pos.x, 0)
    return _pos


def get_directions_pos(game_map, ship):
    surrouding_positions = ship.position.get_surrounding_cardinals() + [ship.position]
    for n, sur_pos in enumerate(surrouding_positions.copy()):
        surrouding_positions[n] = correct_coordinates(game_map, sur_pos)
    directions_dict = {}
    for n, direction in enumerate(directions):
        directions_dict[direction] = surrouding_positions[n]
    return directions_dict


def cells_around(game_map, position, rad):
    x_poss = list(range(position.x - rad, position.x + rad))
    y_poss = list(range(position.y - rad, position.y + rad))
    cells = []
    for x in x_poss:
        for y in y_poss:
            cells.append(correct_coordinates(game_map, Position(x, y)))
    cells.remove(position)
    return cells


def halite_in_cells_around_pos(game_map, position, rad):
    cells = cells_around(game_map, position, rad)
    halite_in_cells = {}
    for cell in cells:
        halite_in_cells[(cell.x, cell.y)] = game_map[cell].halite_amount

    return halite_in_cells


def closest_way_to_deposite(game_map, player, ship):
    deposite_ways = player.get_dropoffs() + [player.shipyard]
    deposite_distances = {}
    for n, deposite_way in enumerate(deposite_ways):
        deposite_distances[n] = game_map.calculate_distance(ship.position, deposite_way.position)

    return deposite_ways[min(deposite_distances, key=deposite_distances.get)]


def posibility_create_dropoff(game_map, player, ship, forcedly=False):
    closest_deposite = closest_way_to_deposite(game_map, player, ship)
    if (game_map.calculate_distance(ship.position, closest_deposite.position) >= 10 or forcedly) \
            and player.halite_amount >= constants.DROPOFF_COST:
        halite_around = sum(halite_in_cells_around_pos(game_map, ship.position, 4).values())
        logging.debug(f"drop. halite ar {halite_around} ")
        if halite_around >= constants.MAX_HALITE * 20:
            return True
    return False


def ship_move(game_map, ship, position, posible_directions_dict, will_occuped_cells):
    ship_direction = game_map.naive_navigate(ship, position)
    if ship_direction not in posible_directions_dict.keys():
        me = ship.owner
        directions_dict = get_directions_pos(game_map, ship)
        for direction, coord in directions_dict.copy().items():
            if game_map[coord].ship and game_map[coord].ship.owner != me:
                directions_dict.pop(direction)
                continue
            cells_in_2 = [Position(coord.x-1, coord.y),
                          Position(coord.x+1, coord.y),
                          Position(coord.x, coord.y-1),
                          Position(coord.x, coord.y+1)]
            cells_in_2 = [correct_coordinates(game_map, pos) for pos in cells_in_2]
            for cell in cells_in_2:
                if game_map[cell].ship and game_map[cell].ship.owner != me:
                    directions_dict.pop(direction)
                    break

            
        # cell_around_in_2 = cells_around(game_map, ship.position, 2)
        # cell_around_in_1 = cells_around(game_map, ship.position, 1)
        # cell_around_in_2 = [cell for cell in  cell_around_in_2 if cell not in cell_around_in_1]
        # directions_in_2 = [Position(ship.position.x-2, ship.position.y),
        #                   Position(ship.position.x+2, ship.position.y),
        #                   Position(ship.position.x, ship.position.y-2),
        #                   Position(ship.position.x, ship.position.y+2)]
        # directions_in_2 = [correct_coordinates(game_map, pos) for pos in directions_in_2]
        # for cell in directions_in_2:
        #     if game_map[cell].ship and game_map[cell].ship.owner != me:
        #         pass
        if len(directions_dict) == 1:
            ship_direction = directions_dict.keys()[0]
        elif len(directions_dict) > 0:
            ship_direction = random.choice(directions_dict.keys())
        else:
            return ship.stay_still()

        will_occuped_cells.append(directions_dict[ship_direction])
        logging.info('ship ID {} (FULL) moves to pos {}'.format(ship.id, directions_dict[ship_direction]))
        return ship.move(ship_direction)

    will_occuped_cells.append(posible_directions_dict[ship_direction])
    logging.info('ship ID {} (FULL) moves to pos {}'.format(ship.id, posible_directions_dict[ship_direction]))
    return ship.move(ship_direction)


def closes_enemy_ship(game_map, ship, enemy_ships):
    closest_enemy = enemy_ships[0]
    distance = game_map.calculate_distance(ship.position, enemy_ships[0].position)
    for enemy_ship in enemy_ships[0:]:
        _distance = game_map.calculate_distance(ship.position, enemy_ship.position)
        if _distance > distance:
            closest_enemy = enemy_ship
            distance = _distance
    return closest_enemy, distance


def try_attack_enemy(game_map, ship, enemy_ship, my_occuped_cells, will_occuped_cells):
    directions_dict = get_directions_pos(game_map, ship)
    for direction in game_map.get_unsafe_moves(ship.position, enemy_ship.position):
        if directions_dict[direction] in my_occuped_cells:
            continue
        else:
            logging.info("ship ID {} moves to {}, try to attack enemy ship ID {} in {}".format(
                ship.id, directions_dict[direction], enemy_ship.id, enemy_ship.position))
            will_occuped_cells.append(directions_dict[direction])
            return ship.move(direction)

""" <<<Game Loop>>> """

directions = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]
full_ships_id = []
MAX_SHIPS = 0
halite_on_map = 0
HALITE_FOR_PLAYER = 0
MIN_HALITE = constants.DROPOFF_COST + constants.SHIP_COST
while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    if game.turn_number == 1:
        height = game_map.height
        width = game_map.width
        for y in range(height):
            for x in range(width):
                halite_on_map += game_map[Position(x, y)].halite_amount
        logging.info(f'halite on map: {halite_on_map}')
        logging.info(f'players: {len(game.players)}')
        HALITE_FOR_PLAYER = halite_on_map / len(game.players)
        MAX_SHIPS = int(HALITE_FOR_PLAYER * .4 / constants.SHIP_COST)
        logging.info(f'HALITE_FOR_PLAYER: {HALITE_FOR_PLAYER}')
        logging.info(f'MAX_SHIPS: {MAX_SHIPS}')

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []
    my_occuped_cells = [ship.position for ship in me.get_ships()]
    occuped_cells = [] + my_occuped_cells

    #  find full enemy ships
    players = [player for player in game.players.values() if player != me]
    full_enough_enemy_ships = []
    for player in players:
        for ship in player.get_ships():
            cells = cells_around(game_map, ship.position, 1)
            occuped_cells += cells
            for cell in cells:
                game_map[cell].mark_unsafe(ship)
            if ship.halite_amount >= constants.MAX_HALITE * .5 \
                and game_map.calculate_distance(ship.position,
                                                closest_way_to_deposite(game_map, player, ship).position) >= 4:
                full_enough_enemy_ships.append(ship)


    # logging.debug("occuped cells by me and others: {}".format(occuped_cells))

    will_occuped_cells = []
    for n, will_occuped_cell in enumerate(will_occuped_cells.copy()):
        _will_occuped_cell = correct_coordinates(game_map, will_occuped_cell)
        if _will_occuped_cell != will_occuped_cell:
            will_occuped_cells.pop(n)
            will_occuped_cells.append(_will_occuped_cell)

    my_ships = me.get_ships()
    if len(my_ships) > MAX_SHIPS:
        MAX_SHIPS = len(my_ships)
    not_full_ships = my_ships.copy()

    # check full ships for exist and del fron not_full_ships
    for ship_id in full_ships_id.copy():
        if not me.has_ship(ship_id):
            full_ships_id.remove(ship_id)
            continue
        ship = me.get_ship(ship_id)
        if ship.halite_amount <= constants.MAX_HALITE / 3:
            full_ships_id.remove(ship_id)
        else:
            not_full_ships.remove(ship)

    # creates drop forcedly
    will_create_deposite_pos = []
    if full_ships_id:
        if len(full_ships_id) / len(my_ships) > 0.4 and len(my_ships) > 8 and me.halite_amount >= constants.DROPOFF_COST:
            max_distance_id = {}
            for ship_id in full_ships_id:
                ship = me.get_ship(ship_id)
                if posibility_create_dropoff(game_map, me, ship):
                    max_distance_id[ship_id] = game_map.calculate_distance(ship.position,
                                                                           closest_way_to_deposite(game_map, me, ship).position)
            if max_distance_id:
                ship = me.get_ship(max(max_distance_id, key=max_distance_id.get))
                will_create_deposite_pos.append(ship.position)
                command_queue.append(ship.make_dropoff())
                me.halite_amount -= constants.DROPOFF_COST
                logging.info("ship ID {} FORCEDLY creates dropoff at pos {}".format(ship.id, ship.position))
                full_ships_id.remove(ship.id)\

    # then close to end
    if game.turn_number > constants.MAX_TURNS * .92:
        for ship in not_full_ships.copy():
            if ship.halite_amount >= constants.MAX_HALITE * .4:
                distance = game_map.calculate_distance(ship.position,
                                                       closest_way_to_deposite(game_map, me, ship).position)
                if distance + 3 < constants.MAX_TURNS - game.turn_number:
                    if full_enough_enemy_ships:  # attack
                        enemy_ship, distance_to_enemy = closes_enemy_ship(game_map, ship, full_enough_enemy_ships)
                    else:
                        distance_to_enemy = float('inf')
                    if distance_to_enemy <= 4:
                        command_queue.append(
                            try_attack_enemy(game_map, ship, enemy_ship, my_occuped_cells, will_occuped_cells))
                else:
                    full_ships_id.append(ship.id)
                not_full_ships.remove(ship)

    # full ship goes to drop
    for ship_id in full_ships_id:
        ship = me.get_ship(ship_id)
        directions_dict = get_directions_pos(game_map, ship)
        for direction in directions_dict.copy():
            target_cell = directions_dict[direction]
            if (target_cell in will_occuped_cells or target_cell in occuped_cells) and direction != Direction.Still:
                directions_dict.pop(direction)

        if posibility_create_dropoff(game_map, me, ship):
            if will_create_deposite_pos:
                depos_distance = []
                for depos in will_create_deposite_pos:
                    depos_distance.append(game_map.calculate_distance(ship.position, depos))
                if min(depos_distance) <= 9:
                    pass
                else:
                    will_create_deposite_pos.append(ship.position)
                    command_queue.append(ship.make_dropoff())
                    me.halite_amount -= constants.DROPOFF_COST
                    logging.info("ship ID {} creates dropoff at pos {}".format(ship_id, ship.position))

            else:
                will_create_deposite_pos.append(ship.position)
                command_queue.append(ship.make_dropoff())
                me.halite_amount -= constants.DROPOFF_COST
                logging.info("ship ID {} creates dropoff at pos {}".format(ship_id, ship.position))

        else:
            closest_deposite = closest_way_to_deposite(game_map, me, ship)

            if not game_map[closest_deposite.position].is_occupied:
                command_queue.append(ship_move(game_map, ship, closest_deposite.position, directions_dict, will_occuped_cells))

            elif game_map.calculate_distance(ship.position, closest_deposite.position) == 2:
                command_queue.append(ship.stay_still())

            else:
                command_queue.append(ship_move(game_map, ship, closest_deposite.position, directions_dict, will_occuped_cells))


    for ship in not_full_ships:
        directions_dict = get_directions_pos(game_map, ship)

        for direction in directions_dict.copy():
            target_cell = directions_dict[direction]
            if (target_cell in will_occuped_cells or target_cell in occuped_cells) and direction != Direction.Still:
                directions_dict.pop(direction)

        if ship.halite_amount >=  constants.MAX_HALITE * .8 or (game.turn_number <= 50 and ship.halite_amount >= constants.MAX_HALITE * .6
                            and not game_map[ship.position].halite_amount >= constants.MAX_HALITE * .4):
            full_ships_id.append(ship.id)

        if ship.position == me.shipyard.position:
            ship_direction = random.choice(list(directions_dict.keys()))
            target_cell = directions_dict[ship_direction]
            while target_cell in will_occuped_cells or target_cell in occuped_cells:
                directions_dict.pop(ship_direction)
                if len(directions_dict) == 0:
                    ship_direction = Direction.Still
                    break
                elif not len(directions_dict) == 1:
                    ship_direction = random.choice(list(directions_dict.keys()))
                else:
                    ship_direction = list(directions_dict.keys())[0]
                target_cell = directions_dict[ship_direction]

            logging.info('ship ID {} moves to pos {}'.format(ship.id, target_cell))
            # ship_direction = directions_dict[target_cell]
            command_queue.append(
                ship.move(
                    ship_direction))
            will_occuped_cells.append(target_cell)

        elif game_map[ship.position].halite_amount < constants.MAX_HALITE / 10:
            if full_enough_enemy_ships:
                enemy_ship, distance_to_enemy = closes_enemy_ship(game_map, ship, full_enough_enemy_ships)
            else:
                distance_to_enemy = float('inf')
            if len(my_ships) >= 10 and ship.halite_amount <= constants.MAX_HALITE / 9 and distance_to_enemy <= 4:
                command_queue.append(try_attack_enemy(game_map, ship, enemy_ship, my_occuped_cells, will_occuped_cells))

            else:
                priority_cells = {}
                for cell_cords, halite_amount in halite_in_cells_around_pos(game_map, ship.position, 3).items():
                    distance = game_map.calculate_distance(ship.position, Position(cell_cords[0], cell_cords[1]))
                    if distance != 0:
                        priority_cells[cell_cords] = halite_amount / distance
                x, y = max(priority_cells, key=priority_cells.get)
                ship_direction = game_map.naive_navigate(ship, Position(x, y))
                while ship_direction not in directions_dict.keys() or ship_direction == Direction.Still:
                    priority_cells.pop(max(priority_cells, key=priority_cells.get))
                    if len(priority_cells) == 0:
                        break
                    x, y = max(priority_cells, key=priority_cells.get)
                    ship_direction = game_map.naive_navigate(ship, Position(x, y))

                target_cell = directions_dict[ship_direction]
                logging.info('ship ID {} moves to pos {}'.format(ship.id, target_cell))
                command_queue.append(
                    ship.move(
                        ship_direction))
                will_occuped_cells.append(target_cell)

        else:
            command_queue.append(ship.stay_still())

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if (game.turn_number <= constants.MAX_TURNS/3 or len(my_ships) <= MAX_SHIPS/3) \
            and game.turn_number < constants.MAX_TURNS * .6 \
            and ((game.turn_number <= constants.MAX_TURNS/3 and me.halite_amount >= constants.SHIP_COST)
                 or me.halite_amount >= MIN_HALITE) and not game_map[me.shipyard].is_occupied:
        logging.info('spawn ship')
        command_queue.append(me.shipyard.spawn())
        me.halite_amount -= constants.SHIP_COST

    # Send your moves back to the game environment, ending this turn.
    # logging.debug(f"command queue {command_queue}")
    game.end_turn(command_queue)

