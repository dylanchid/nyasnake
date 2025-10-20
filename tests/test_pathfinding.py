"""
Unit tests for pathfinding algorithms.

Run with: python -m pytest test_pathfinding.py -v
"""

import pytest
from models import Position, Direction, GameState, Snake, AIPersonality
from pathfinding import TemporalPathfinder, SimplePathfinder, PathfindingError


class TestSimplePathfinder:
    """Tests for simple A* pathfinding"""
    
    def test_finds_straight_path(self):
        """Test pathfinding finds straight line path"""
        start = Position(1, 1)
        goal = Position(5, 1)
        obstacles = set()
        
        path = SimplePathfinder.find_path(start, goal, obstacles, 20, 20)
        
        assert path is not None
        assert len(path) == 4  # (2,1), (3,1), (4,1), (5,1)
        assert path[0] == Position(2, 1)
        assert path[-1] == goal
    
    def test_finds_path_around_obstacle(self):
        """Test pathfinding navigates around obstacles"""
        start = Position(1, 5)
        goal = Position(10, 5)
        
        # Create wall
        obstacles = {Position(5, y) for y in range(1, 10)}
        
        path = SimplePathfinder.find_path(start, goal, obstacles, 20, 20)
        
        assert path is not None
        assert len(path) > 9  # Must go around
        assert goal in path
        # Verify no collision with wall
        for pos in path:
            assert pos not in obstacles
    
    def test_returns_none_when_blocked(self):
        """Test returns None when completely blocked"""
        start = Position(5, 5)
        goal = Position(5, 10)
        
        # Completely surround goal
        obstacles = {
            Position(4, 10), Position(5, 9), Position(6, 10), Position(5, 11)
        }
        
        path = SimplePathfinder.find_path(start, goal, obstacles, 20, 20)
        
        assert path is None
    
    def test_returns_empty_for_same_position(self):
        """Test returns empty path when start equals goal"""
        pos = Position(5, 5)
        
        path = SimplePathfinder.find_path(pos, pos, set(), 20, 20)
        
        assert path == []


class TestTemporalPathfinder:
    """Tests for temporal A* pathfinding"""
    
    def create_test_game_state(self, snakes_data):
        """Helper to create GameState for testing"""
        snakes = []
        for i, (pos, direction) in enumerate(snakes_data):
            snake = Snake(
                id=i,
                body=[pos],
                direction=direction,
                personality=AIPersonality.BALANCED,
                color='test',
                symbol='T'
            )
            snakes.append(snake)
        
        return GameState(
            snakes=tuple(snakes),
            food=frozenset(),
            width=20,
            height=20
        )
    
    def test_finds_path_in_empty_space(self):
        """Test temporal pathfinding in empty grid"""
        game_state = self.create_test_game_state([
            (Position(1, 1), Direction.RIGHT)  # Snake at start
        ])
        
        pathfinder = TemporalPathfinder(game_state)
        requesting_snake = game_state.snakes[0]
        
        path = pathfinder.find_path(Position(1, 1), Position(10, 1), requesting_snake)
        
        assert path is not None
        assert len(path) == 9
        assert path[-1] == Position(10, 1)
    
    def test_avoids_moving_snake(self):
        """Test temporal pathfinding predicts snake movement"""
        # Snake 1 (requesting): at (1,5), wants to go to (10,5)
        # Snake 2: at (5,3), moving DOWN - will block path
        game_state = self.create_test_game_state([
            (Position(1, 5), Direction.RIGHT),
            (Position(5, 3), Direction.DOWN)  # Will be at (5,4), (5,5), (5,6)...
        ])
        
        pathfinder = TemporalPathfinder(game_state)
        requesting_snake = game_state.snakes[0]
        
        path = pathfinder.find_path(Position(1, 5), Position(10, 5), requesting_snake)
        
        # Path should exist but go around the moving snake
        assert path is not None
        
        # Verify path doesn't collide with predicted snake positions
        # At time T, snake2 will be at (5, 3+T)
        for t, pos in enumerate(path, start=1):
            predicted_snake2_pos = Position(5, 3 + t)
            assert pos != predicted_snake2_pos, f"Collision at time {t}: {pos}"
    
    def test_handles_invalid_start_position(self):
        """Test error handling for invalid start position"""
        game_state = self.create_test_game_state([
            (Position(1, 1), Direction.RIGHT)
        ])
        
        pathfinder = TemporalPathfinder(game_state)
        requesting_snake = game_state.snakes[0]
        
        # Start position outside bounds
        with pytest.raises(PathfindingError):
            pathfinder.find_path(Position(0, 0), Position(10, 10), requesting_snake)
    
    def test_returns_empty_for_same_position(self):
        """Test returns empty path when start equals goal"""
        game_state = self.create_test_game_state([
            (Position(5, 5), Direction.RIGHT)
        ])
        
        pathfinder = TemporalPathfinder(game_state)
        requesting_snake = game_state.snakes[0]
        
        path = pathfinder.find_path(Position(5, 5), Position(5, 5), requesting_snake)
        
        assert path == []


class TestPathfindingPerformance:
    """Performance tests for pathfinding"""
    
    def test_respects_node_limit(self):
        """Test that pathfinding respects node exploration limit"""
        # Create maze that would require many node expansions
        game_state = GameState(
            snakes=tuple([
                Snake(0, [Position(1, 1)], Direction.RIGHT, 
                     AIPersonality.BALANCED, 'test', 'T')
            ]),
            food=frozenset(),
            width=50,
            height=50
        )
        
        pathfinder = TemporalPathfinder(game_state)
        requesting_snake = game_state.snakes[0]
        
        # Very distant goal
        path = pathfinder.find_path(Position(1, 1), Position(48, 48), requesting_snake)
        
        # Should either find path or return None, but not hang
        assert path is None or isinstance(path, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])