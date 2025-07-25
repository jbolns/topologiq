import random
import numpy as np
from typing import Tuple, List, Optional

from utils.classes import StandardCoord, StandardBeam, NodeBeams, StandardBlock


def check_is_exit(
    source_coord: StandardCoord, source_kind: Optional[str], target_coord: StandardCoord
) -> bool:
    """Checks if a face is an exit by matching exit markers in the block/pipe's symbolic name
    and an displacement array symbolising the direction of the target block/pipe.

    Args:
        - source_coord: (x, y, z) coordinates for the current block/pipe.
        - source_kind: current block's/pipe's kind.
        - target_coord: coordinates for the target block/pipe.

    Returns:
        - bool:
            - True: face is an exist
            - False: face is not an exit.

    """

    source_kind = source_kind.lower()[:3] if isinstance(source_kind, str) else ""
    kind_3D = [source_kind[0], source_kind[1], source_kind[2]]

    if "o" in kind_3D:
        exit_marker = "o"
    else:
        exit_marker = [i for i in set(kind_3D) if kind_3D.count(i) == 2][0]

    valid_exit_indices = [i for i, char in enumerate(kind_3D) if char == exit_marker]
    displacements = [
        target - source for source, target in zip(source_coord, target_coord)
    ]

    displacement_axis_index = -1
    for i, disp in enumerate(displacements):
        if disp != 0:
            displacement_axis_index = i
            break

    if displacement_axis_index != -1 and displacement_axis_index in valid_exit_indices:
        return True
    else:
        return False


def check_unobstructed(
    source_coord: StandardCoord,
    target_coord: StandardCoord,
    occupied: List[StandardCoord],
    all_beams: List[NodeBeams],
    length_of_beams: int,
) -> Tuple[bool, StandardBeam]:
    """Checks if a face (typically an exit: call after verifying face is exit) is unobstructed.

    Args:
        - source_coord: (x, y, z) coordinates for the current block/pipe.
        - target_coord: coordinates for the target block/pipe.
        - occupied: list of coordinates occupied by any blocks/pipes placed as a result of previous operations.
        - all_beams: list of coordinates occupied by the beams of all blocks in original ZX-graph
        - length_of_beams: int representing how long does each beam spans from its originating block.

    Returns:
        - bool:
            - True: face is unobstructed
            - False: face is obstructed.

    """

    single_beam_for_exit: StandardBeam = []

    directions = [target - source for source, target in zip(source_coord, target_coord)]
    directions = [1 if d > 0 else -1 if d < 0 else 0 for d in directions]

    for i in range(1, length_of_beams):
        dx, dy, dz = (directions[0] * i, directions[1] * i, directions[2] * i)
        single_beam_for_exit.append(
            (source_coord[0] + dx, source_coord[1] + dy, source_coord[2] + dz)
        )

    if not occupied:
        return True, single_beam_for_exit

    for coord in single_beam_for_exit:
        if coord in occupied or coord in all_beams:
            return False, single_beam_for_exit

    return True, single_beam_for_exit


def check_for_exits(
    node_coords: StandardCoord,
    node_kind: str | None,
    occupied: List[StandardCoord],
    all_beams: List[NodeBeams],
    length_of_beams: int,
) -> Tuple[int, NodeBeams]:
    """Finds the number of unobstructed exits for any given block/pipe by calling other functions that use the
    block's/pipe's symbolic name to determine if each face is or is not
    and whether the said exit is unobstructed.

    Args:
        - node_coords: (x, y, z) coordinates for the block/pipe of interest.
        - node_kind: kind/type of the block/pipe of interest.
        - occupied: list of coordinates occupied by any blocks/pipes placed as a result of previous operations.
        - all_beams: list of coordinates occupied by the beams of all blocks in original ZX-graph
        - length_of_beams: int representing how long does each beam spans from its originating block.

    Returns:
        - unobstructed_exits_n: the number of unobstructed exist for the block/pipe of interest.
        - node_beams: the beams emanating from the block/pipe of interest.

    """

    unobstructed_exits_n = 0
    node_beams: NodeBeams = []

    directional_array = [
        (1, 0, 0),
        (-1, 0, 0),
        (0, 1, 0),
        (0, -1, 0),
        (0, 0, 1),
        (0, 0, -1),
    ]

    for d in directional_array:
        target_coords = (
            node_coords[0] + d[0],
            node_coords[1] + d[1],
            node_coords[2] + d[2],
        )

        if check_is_exit(node_coords, node_kind, target_coords):
            is_unobstructed, exit_beam = check_unobstructed(
                node_coords, target_coords, occupied, all_beams, length_of_beams
            )
            if is_unobstructed:
                unobstructed_exits_n += 1
                node_beams.append(exit_beam)

    return unobstructed_exits_n, node_beams


def is_move_allowed(source_coords: StandardCoord, next_coords: StandardCoord) -> bool:
    """Uses a Manhattan distance to quickly checks if a potential (source, target) combination
    is possible given the standard size of a block and pipe and that all blocks are followed by a pipe.

    Args:
        - source_coords: (x, y, z) coordinates for the originating block.
        - next_coords: (x, y, z) coordinates for the potential placement of the target block.

    Returns:
        - bool:
            - True: move is theoretically possible,
            - False: move is not theoretically possible.

    """

    sx, sy, sz = source_coords
    nx, ny, nz = next_coords
    manhattan_distance = abs(nx - sx) + abs(ny - sy) + abs(nz - sz)
    return manhattan_distance % 3 == 0


def generate_tentative_target_positions(
    source_coords: StandardCoord,
    step: int = 3,
    occupied_coords: List[StandardCoord] = [],
) -> List[StandardCoord]:
    """Generates a number of potential placement positions for target node.

    Args:
        - source_coords: (x, y, z) coordinates for the originating block.
        - step: intended (Manhattan) distance between origin and target blocks.
        - occupied_coords: a list of coordinates already occupied by previous operations.

    Returns:
        - potential_targets: a list of coordinates that make good candidates for placing the target block.

    """

    # EXTRACT SOURCE COORDS
    sx, sy, sz = source_coords
    potential_targets: List[StandardCoord] = []

    # SINGLE MOVES
    if step == 3:
        targets = [
            (sx + 3, sy, sz),
            (sx - 3, sy, sz),
            (sx, sy + 3, sz),
            (sx, sy - 3, sz),
            (sx, sy, sz + 3),
            (sx, sy, sz - 3),
        ]
        potential_targets = [
            coords for coords in targets if coords not in occupied_coords
        ]

    # DOUBLE MOVES (Manhattan distance 6)
    elif step == 6:
        targets = set()
        for dx in [-3, 3]:
            for dy in [-3, 3]:
                targets.add((sx + dx, sy + dy, sz))
            for dx in [-3, 3]:
                for dz in [-3, 3]:
                    targets.add((sx + dx, sy, sz + dz))
            for dy in [-3, 3]:
                for dz in [-3, 3]:
                    targets.add((sx, sy + dy, sz + dz))
        potential_targets = [
            coords for coords in targets if coords not in occupied_coords
        ]

    # TRIPLE MOVES (Manhattan distance 9)
    elif step == 9:
        targets = set()
        for dx in [-3, 3]:
            for dy in [-3, 3]:
                for dz in [-3, 3]:
                    if abs(dx) + abs(dy) + abs(dz) == 9:
                        targets.add((sx + dx, sy + dy, sz + dz))
        potential_targets = [
            coords for coords in targets if coords not in occupied_coords
        ]

    # ANY STEP HIGHER THAN 9 (step is Manhattan distance, multiple of 3)
    elif step > 9 and step % 3 == 0:
        valid_targets = set()
        attempts = 0
        max_attempts = 500  # Limit attempts to avoid infinite loops in dense spaces
        while len(valid_targets) < 12 and attempts < max_attempts:
            remaining_steps = step
            current_x = sx
            current_y = sy
            current_z = sz

            # Move along x
            move_x = random.choice(range(-remaining_steps, remaining_steps + 1, 3))
            current_x += move_x
            remaining_steps -= abs(move_x)

            # Move along y
            move_y = random.choice(range(-remaining_steps, remaining_steps + 1, 3))
            current_y += move_y
            remaining_steps -= abs(move_y)

            # Move along z (remaining distance)
            move_z = remaining_steps
            current_z += move_z

            if (
                abs(move_x) + abs(move_y) + abs(move_z) == step
                and (current_x, current_y, current_z) not in occupied_coords
            ):
                valid_targets.add((current_x, current_y, current_z))

            # Try other permutations
            permutations = [
                (move_x, move_y, move_z),
                (move_x, move_z, move_y),
                (move_y, move_x, move_z),
                (move_y, move_z, move_x),
                (move_z, move_x, move_y),
                (move_z, move_y, move_x),
            ]

            for mx, my, mz in permutations:
                cx, cy, cz = sx + mx, sy + my, sz + mz
                if (
                    abs(mx) + abs(my) + abs(mz) == step
                    and (cx, cy, cz) not in occupied_coords
                ):
                    valid_targets.add((cx, cy, cz))

            attempts += 1

        potential_targets = list(valid_targets)

    return potential_targets


def prune_all_beams(
    all_beams: List[NodeBeams], occupied_coords: List[StandardCoord]
) -> List[NodeBeams]:
    """Removes beams that have already been broken, as these are no longer indicative of anything.

    Args:
        - all_beams: list of coordinates occupied by the beams of all blocks in original ZX-graph
        - occupied_coords: list of coordinates occupied by any blocks/pipes placed as a result of previous operations.

    Returns:
        - new_all_beams: list of beams without any beams where any of the coordinates in the path of the beam overlap with occupied coords.

    """

    try:
        new_all_beams = []
        for node_beams in all_beams:
            new_node_beams = []
            for single_beam in node_beams:
                if all([coord not in occupied_coords for coord in single_beam]):
                    new_node_beams.append(single_beam)
            if new_node_beams:
                new_all_beams.append(new_node_beams)
    except:
        new_all_beams = all_beams

    return new_all_beams


def build_newly_indexed_path_dict(
    edge_paths: dict,
) -> Tuple[dict[int, StandardBlock], dict[Tuple[int, int], str]]:
    """Distils an edge_path object into a final list of nodes/blocks and edges/pipes for the space-time diagram.

    Args:
        - edge_paths: a dictionary containing a number of edge paths, i.e., full paths between two blocks, each path made of 3D blocks and pipes.

    Returns:
        - lattice_nodes: the nodes/blocks of the resulting space-time diagram (without redundant blocks)
        - lattice_edges: the edges/pipes of the resulting space-time diagram (without redundant pipes)

    """

    max_id = 0
    indexed_paths = {}
    for edge_path in edge_paths.values():
        max_id = max(max_id, edge_path["src_tgt_ids"][0], edge_path["src_tgt_ids"][1])
    next_id = max_id + 1

    for edge_path in edge_paths.values():

        indexed_path = {}
        start_key, end_key = edge_path["src_tgt_ids"]
        nodes_in_path = edge_path["path_nodes"]

        indexed_path[start_key] = nodes_in_path[0]

        for i in range(1, len(nodes_in_path) - 1):
            intermediate_node = nodes_in_path[i]
            indexed_path[next_id] = intermediate_node
            next_id += 1

        if len(nodes_in_path) > 1:
            indexed_path[end_key] = nodes_in_path[-1]

        indexed_paths[(start_key, end_key)] = indexed_path

    final_edges = []
    for original_edge_key, path_id_value_map in indexed_paths.items():

        node_ids = list(path_id_value_map.keys())

        block_ids = []
        edge_ids = []
        for i in range(len(node_ids)):
            if i % 2 == 0:
                block_ids.append(node_ids[i])
            else:
                edge_ids.append(node_ids[i])

        if len(block_ids) >= 2:
            for i in range(len(block_ids) - 1):
                node1 = block_ids[i]
                node2 = block_ids[i + 1]
                edge_type = path_id_value_map[edge_ids[i]][1]

                final_edges.append({(node1, node2): edge_type})

    latice_nodes: dict[int, StandardBlock] = {}
    latice_edges: dict[Tuple[int, int], str] = {}
    for item in indexed_paths.values():

        keys = list(item.keys())

        i = 0
        for node_key, node_info in item.items():
            if i % 2 == 0:
                latice_nodes[node_key] = node_info
            else:
                edge_key = (keys[i - 1], keys[i + 1])
                edge_type = node_info[1]
                latice_edges[edge_key] = edge_type
            i += 1

    return latice_nodes, latice_edges


def rotate_o_types(pipe_type: str) -> str:
    """Rotates a pipe around its length by using the exit marker in its symbolic name to create a rotational matrix,
    which is then used to rotate the original name with a symbolic multiplication.

    Args:
        - pipe_type: the type/kind/name of the pipe that needs rotation.

    Returns:
        - rotated_name: a new type/kind/name with the rotation incorporated into the new name.

    """

    h_flag = False
    if "h" in pipe_type:
        h_flag = True
        pipe_type.replace("h", "")

    # Build rotation matrix based on placement of "o" node
    available_indexes = [0, 1, 2]
    available_indexes.remove(pipe_type.index("o"))

    new_matrix = {
        pipe_type.index("o"): np.eye(3, dtype=int)[pipe_type.index("o")],
        available_indexes[0]: np.eye(3, dtype=int)[available_indexes[1]],
        available_indexes[1]: np.eye(3, dtype=int)[available_indexes[0]],
    }

    rotation_matrix = np.array([new_matrix[0], new_matrix[1], new_matrix[2]])

    # Rotate kind
    rotated_name = ""
    for row in rotation_matrix:
        entry = ""
        for j, element in enumerate(row):
            entry += abs(int(element)) * pipe_type[j]
        rotated_name += entry

    if h_flag:
        rotated_name += "h"

    return rotated_name


def adjust_hadamards_direction(pipe_type: str) -> str:
    """ Quickly flips a Hadamard for the opposite Hadamard with length on the same axis. 
    
    Args:
        - pipe_type: the type/kind/name of the Hadamard that needs inverting.
    
    Returns:
        - pipe_type: the type/kind/name of the corresponding/inverted Hadamard.
    
    
    """
    # List of hadamard equivalences
    hdm_equivalences = {"zxoh": "xzoh", "xozh": "zoxh", "oxzh": "ozxh"}

    # Match to equivalent block given direction
    if pipe_type in hdm_equivalences.keys():
        pipe_type = hdm_equivalences[pipe_type]
    else:
        inv_equivalences = {value: key for key, value in hdm_equivalences.items()}
        pipe_type = inv_equivalences[pipe_type]

    # Return revised kind
    return pipe_type
