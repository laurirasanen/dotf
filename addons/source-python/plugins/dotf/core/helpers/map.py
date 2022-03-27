"""
================================================================
    * core/helpers/map.py
    *
    * Copyright (c) 2021 Lauri Räsänen
    * ================================

    ...
================================================================
"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# dotf
from ..map.mapmanager import MapManager
from .enums import Team


def get_closest_lane(origin, team):
    lane_count = MapManager.instance().lane_count
    closest_nodes = []
    closest_node = None
    closest_dist = float("inf")
    for x in range(lane_count):
        nodes = MapManager.instance().get_lane_nodes(x)
        for node in nodes:
            dist = origin.get_distance(node["origin"])
            if dist < closest_dist:
                closest_dist = dist
                closest_nodes = nodes
                closest_node = node

    second_node = None
    direction = 1 if team == Team.BLU else -1
    next_node = None
    prev_node = None

    # Get next node
    if (
        len(nodes) > closest_node["index"] + direction
        and closest_node["index"] + direction >= 0
    ):
        next_node = closest_nodes[closest_node["index"] + direction]

    # Get prev node
    if (
        len(nodes) > closest_node["index"] - direction
        and closest_node["index"] - direction >= 0
    ):
        prev_node = closest_nodes[closest_node["index"] - direction]

    # Figure out which to use
    if next_node == None:
        second_node = prev_node
    elif prev_node == None:
        second_node = next_node
    else:
        # Both nodes valid, figure out which side we are on
        dir_next = next_node["origin"] - closest_node["origin"]
        dir_to_closest = closest_node["origin"] - origin
        # Are we between closest and next?
        if dir_next.dot(dir_to_closest) < 0:
            second_node = next_node
        else:
            second_node = prev_node

    # This is the line we want to be on
    start = None
    end = None
    if (closest_node["index"] < second_node["index"] and direction < 0) or (
        closest_node["index"] > second_node["index"] and direction > 0
    ):
        end = closest_node["origin"]
        start = second_node["origin"]
    else:
        end = second_node["origin"]
        start = closest_node["origin"]

    return start, end
