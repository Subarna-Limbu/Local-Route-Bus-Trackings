def dijkstra(graph, start, end):
    """
    Compute the shortest path using Dijkstra's algorithm.
    
    graph: dict, where keys are node names and values are lists
           of tuples (neighbor, weight).
    start: starting node
    end: destination node
    
    Returns the shortest distance from start to end.
    """
    # Initialize distances: set to infinity except for start node.
    distances = {node: float('inf') for node in graph}
    distances[start] = 0
    visited = set()
    queue = [(0, start)]

    while queue:
        # Sort queue so that the smallest distance is first.
        queue.sort(key=lambda x: x[0])
        current_distance, node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        if node == end:
            break
        for neighbor, weight in graph.get(node, []):
            new_distance = current_distance + weight
            if new_distance < distances.get(neighbor, float('inf')):
                distances[neighbor] = new_distance
                queue.append((new_distance, neighbor))
    return distances[end]


def is_route_valid(stops, pickup, destination):
    """
    Verify that the 'pickup' exists and is before 'destination' in the stop list.
    """
    if (pickup in stops) and (destination in stops) and (stops.index(pickup) < stops.index(destination)):
        return True
    return False
