import numpy as np
from scipy.optimize import least_squares

# Example: 3 beacons at known positions, with measured distances
# beacons = [(0, 0), (10, 0), (5, 8.66)]  # Triangle of beacons
# distances = [5.0, 5.0, 5.0]  # Measured distances

# position = trilaterate(beacons, distances)
# print(f"Estimated position: {position}")

def trilaterate(beacon_positions: list[tuple[float, float]], 
                distances: list[float]) -> tuple[float, float]:
    """
    Calculate position using trilateration with least squares.
    
    Args:
        beacon_positions: List of (x, y) tuples for each beacon
        distances: List of measured distances to each beacon
    
    Returns:
        (x, y) tuple of estimated position
    """
    if len(beacon_positions) != len(distances) or len(beacon_positions) < 2:
        raise ValueError("Need at least 2 beacons with distances")
    
    # Convert to numpy arrays
    beacons = np.array(beacon_positions)
    dists = np.array(distances)
    
    # Initial guess: centroid of beacons
    initial_guess = np.mean(beacons, axis=0)
    
    def residuals(pos):
        """Calculate residuals: difference between measured and calculated distances."""
        pos_array = np.array(pos)
        calculated_dists = np.linalg.norm(beacons - pos_array, axis=1)
        return calculated_dists - dists
    
    # Solve using least squares
    result = least_squares(residuals, initial_guess, method='lm')
    
    return tuple(result.x)
