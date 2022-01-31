#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction

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
game.ready("MrKotee")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

def get_directions_pos(ship):
    surrouding_positions = ship.position.get_surrounding_cardinals() + [ship.position]
    directions_dict = {}
    for n, direction in enumerate(directions):
        directions_dict[direction] = surrouding_positions[n]
    return directions_dict
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
    will_occuped_cells = []

    for ship_id in full_ships_id.copy():
        if not me.has_ship(ship_id):
            full_ships_id.remove(ship_id)
            continue
        ship = me.get_ship(ship_id)
        if ship.halite_amount <= constants.MAX_HALITE/2:
            full_ships_id.remove(ship_id)

    directions = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]
    my_ships = me.get_ships()
    not_full_ships = my_ships.copy()

    for ship_id in full_ships_id:
        ship = me.get_ship(ship_id)
        directions_dict = get_directions_pos(ship)

        ship_direction = game_map.naive_navigate(ship, me.shipyard.position)
        command_queue.append(
            ship.move(
                ship_direction))

        will_occuped_cells.append(directions_dict[ship_direction])
        logging.info('ship ID {} (FULL) moves to pos {}'.format(ship.id, directions_dict[ship_direction]))
        not_full_ships.remove(ship)

    for ship in not_full_ships:
        directions_dict = get_directions_pos(ship)
        # For each of your ships, move randomly if the ship is on a low halite location or the ship is full.
        #   Else, collect halite.
        if ship.is_full:
            full_ships_id.append(ship.id)

        if game_map[ship.position].halite_amount < constants.MAX_HALITE / 10:

            cells_halite = {}
            # for cell in surrouding_positions:
            #     halite_amount = game_map[cell].halite_amount
            #     cells_halite[halite_amount] = cell
            for direction in directions_dict:
                halite_amount = game_map[directions_dict[direction]].halite_amount
                cells_halite[direction] = halite_amount

            # logging.debug("halite amount dict: {} ".format(str(cells_halite)))

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
                logging.debug('choosed direction: {}'.format(ship_direction))
                target_cell = directions_dict[ship_direction]

            logging.info('ship ID {} moves to pos {}'.format(ship.id, target_cell))
            # ship_direction = directions_dict[target_cell]
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

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

