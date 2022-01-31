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
game.ready("MrKotee_v1")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))
logging.info("map size h={}, w={}".format(game.game_map.height, game.game_map.width))


def correct_coordinates(game_map, pos):
    _pos = pos
    if pos.x < 0:
        _pos = Position(game_map.width-pos.x, pos.y)
    elif pos.x == game_map.width:
        _pos = Position(0, pos.y)
    if pos.y < 0:
        _pos = Position(pos.x, game_map.height-pos.y)
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


def posibility_create_dropoff(game_map, player, ship):
    closest_deposite = closest_way_to_deposite(game_map, player, ship)
    if game_map.calculate_distance(ship.position, closest_deposite.position) >= 10 \
            and player.halite_amount >= constants.DROPOFF_COST:
        halite_around = sum(halite_in_cells_around_pos(game_map, ship.position, 3).values())
        if halite_around >= constants.MAX_HALITE * 15:
            return True
    return False

""" <<<Game Loop>>> """

full_ships_id = []

while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []
    occuped_cells = [ship.position for ship in me.get_ships()]
    players = [player for player in game.players.values() if player != me]
    for player in players:
        for ship in player.get_ships():
            cells = cells_around(game_map, ship.position, 1)
            occuped_cells += cells
            for cell in cells:
                game_map[cell].mark_unsafe(ship)


    will_occuped_cells = []
    for n, will_occuped_cell in enumerate(will_occuped_cells.copy()):
        _will_occuped_cell = correct_coordinates(game_map, will_occuped_cell)
        if _will_occuped_cell != will_occuped_cell:
            will_occuped_cells.pop(n)
            will_occuped_cells.append(_will_occuped_cell)

    for ship_id in full_ships_id.copy():
        if not me.has_ship(ship_id):
            full_ships_id.remove(ship_id)
            continue
        ship = me.get_ship(ship_id)
        if ship.halite_amount <= constants.MAX_HALITE/2:
            if game.turn_number <= 50 and ship.halite_amount >= constants.MAX_HALITE * .5:
                pass

            else:
                full_ships_id.remove(ship_id)

    directions = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]
    my_ships = me.get_ships()
    not_full_ships = my_ships.copy()

    will_create_deposite_pos = []
    for ship_id in full_ships_id:
        ship = me.get_ship(ship_id)
        directions_dict = get_directions_pos(game_map, ship)

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
                ship_direction = game_map.naive_navigate(ship, closest_deposite.position)
                command_queue.append(
                    ship.move(
                        ship_direction))

                will_occuped_cells.append(directions_dict[ship_direction])
                logging.info('ship ID {} (FULL) moves to pos {}'.format(ship.id, directions_dict[ship_direction]))

            elif game_map.calculate_distance(ship.position, closest_deposite.position) <= 3:
                command_queue.append(ship.stay_still())

            else:
                ship_direction = game_map.naive_navigate(ship, closest_deposite.position)
                command_queue.append(
                    ship.move(
                        ship_direction))

                will_occuped_cells.append(directions_dict[ship_direction])
                logging.info('ship ID {} (FULL) moves to pos {}'.format(ship.id, directions_dict[ship_direction]))


        not_full_ships.remove(ship)

    for ship in not_full_ships:
        directions_dict = get_directions_pos(game_map, ship)
        # For each of your ships, move randomly if the ship is on a low halite location or the ship is full.
        #   Else, collect halite.
        if ship.is_full or (game.turn_number <= 50 and ship.halite_amount >= constants.MAX_HALITE * .6
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

            cells_halite = {}
            for direction in directions_dict:
                halite_amount = game_map[directions_dict[direction]].halite_amount
                cells_halite[direction] = halite_amount

            ship_direction = max(cells_halite, key=cells_halite.get)
            target_cell = directions_dict[ship_direction]
            while target_cell in will_occuped_cells or target_cell in occuped_cells:
                # logging.debug('try to find not occuped cell')
                # logging.debug('target_cell: {}, direction: {}'.format(target_cell, ship_direction))
                # logging.debug("halite amount dict: {} ".format(str(cells_halite)))
                cells_halite.pop(min(cells_halite, key=cells_halite.get))
                if not cells_halite:
                    ship_direction = Direction.Still
                    break

                if not len(cells_halite) == 1:
                    ship_direction = random.choice(list(cells_halite.keys()))
                else:
                    ship_direction = list(cells_halite.keys())[0]
                # logging.debug('choosed direction: {}'.format(ship_direction))
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
    if game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        logging.info('spawn ship')
        command_queue.append(me.shipyard.spawn())
        me.halite_amount -= constants.SHIP_COST

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

