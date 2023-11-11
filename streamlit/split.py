import numpy as np


# ---- GEOMETRIC SPLIT ----
# Split the node demand into smaller demands according to a geometric progression
def split_demand_geometric(node_demand, BUS_CAPACITY, fraction, fraction_sum):
    demands = [np.floor(node_demand * (f / fraction_sum)) for f in fraction]
    demands = list(filter(lambda x: x > 0, demands))

    if sum(demands) < node_demand:
        demands[-1] += node_demand - sum(demands)

    i = len(demands) - 1

    while demands[i] >= BUS_CAPACITY * 1:
        new_demand = split_demand_geometric(
            demands[i], BUS_CAPACITY, fraction, fraction_sum
        )
        demands.pop(i)
        demands.extend(new_demand)
        i -= 1

    return demands


# ---- CAPACITY SPLIT ----
# Split the node demand into smaller demands according to BUS_CAPACITY
def split_demand_capacity(node_demand, BUS_CAPACITY):
    demands = [BUS_CAPACITY for _ in range(int(np.floor(node_demand / BUS_CAPACITY)))]
    demands.append(node_demand - sum(demands))

    return demands


# ---- EQUAL SPLIT ----
# Split the node demand into equal demand nodes of 1
def split_demand_equal(node_demand, BUS_CAPACITY):
    demands = [1 for _ in range(node_demand)]

    return demands


# ---- RANDOM SPLIT ----
# Split the node demand into random demand values
def split_demand_random(node_demand, BUS_CAPACITY, rng: np.random.Generator):
    demands = []
    remaining_demand = node_demand

    while remaining_demand > 0:
        demand = rng.integers(1, BUS_CAPACITY)
        demands.append(demand)
        remaining_demand -= demand

    if sum(demands) > node_demand:
        demands[-1] -= sum(demands) - node_demand

    return demands


# Main function to split the demand of a node
def split_demand_node(demand, node, BUS_CAPACITY, rng, split_type: str = "geometric"):
    node_demand = demand[node]
    match split_type:
        case "geometric":
            S = 100
            fraction = [2 ** (i - 1) for i in range(1, S + 1)]
            fraction_sum = sum(fraction)
            demands = split_demand_geometric(
                node_demand, BUS_CAPACITY, fraction, fraction_sum
            )
        case "capacity":
            demands = split_demand_capacity(node_demand, BUS_CAPACITY)
        case "equal":
            demands = split_demand_equal(node_demand, BUS_CAPACITY)
        case "random":
            demands = split_demand_random(node_demand, BUS_CAPACITY, rng)
        case _:
            raise ValueError("Invalid demand split type")

    return {f"{node}_{i}": d for i, d in enumerate(demands, 1)}


def reconstruct_demand(demand, BUS_CAPACITY, rng, split_type: str = "geometric"):
    nodes_exceeding_demand = {}
    new_demand = demand.copy()
    for k, v in demand.items():
        if v > BUS_CAPACITY:
            new_nodes = split_demand_node(demand, k, BUS_CAPACITY, rng, split_type)

            new_demand.pop(k)
            new_demand.update(new_nodes)

            nodes_exceeding_demand[k] = new_nodes

    print(f"New nodes added for: {list(nodes_exceeding_demand.keys())}")

    return new_demand, nodes_exceeding_demand


# Update distance matrix to include split nodes.
# Distance between split nodes of same parent node is 0
def update_distance_matrix(distance_matrix, nodes_exceeding_demand, new_demand):
    distance_matrix_model = distance_matrix.copy()

    for node in nodes_exceeding_demand:
        for i in range(1, len([k for k in new_demand.keys() if node in k]) + 1):
            distance_matrix_model[f"{node}_{i}"] = distance_matrix_model[node]
            distance_matrix_model.loc[f"{node}_{i}"] = distance_matrix_model.loc[node]
            distance_matrix_model.loc[f"{node}_{i}", node] = 0

        distance_matrix_model.drop(columns=[node], index=[node], inplace=True)

    return distance_matrix_model
