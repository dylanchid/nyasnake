"""
Unit tests for AI evaluation and perception.

Run with: python -m pytest test_evaluation.py -v
"""

import pytest
from models import Position, Direction, GameState, Snake, AIPersonality
from ai_core import Perception, SpaceEvaluator, MoveSimulator, StrategicEvaluator
from config import AI_CONFIG


class TestPerception:
    """Tests for Perception class"""
    
    def create_test_game_state(self, snake_data, food_positions=None):
        """Helper to create GameState"""
        snakes = []
        for i, (positions, direction) in enumerate(snake_data):
            snake = Snake(
                id=i,
                body=positions,
                direction=direction,
                personality=AIPersonality.BALANCED,
                color='test',
                symbol='T'
            )
            snakes.append(snake)
        
        food = frozenset(food_positions) if food_positions else frozenset()
        
        return GameState(
            snakes=tuple(snakes),
            food=food,
            width=20,
            height=20
        )
    
    def test_gets_safe_immediate_directions(self):
        """Test identifies safe immediate directions"""
        game_state = self.create_test_game_state([
            ([Position(10, 10)], Direction.RIGHT)
        ])
        
        perception = Perception(game_state)
        snake = game_state.snakes[0]
        
        safe_dirs = perception.get_safe_immediate_directions(snake)
        
        # All directions should be safe in empty space
        assert len(safe_dirs) == 3  # Can't go LEFT (opposite of current direction)
        assert Direction.LEFT not in safe_dirs  # Opposite direction
    
    def test_avoids_walls(self):
        """Test avoids directions leading to walls"""
        # Snake near left wall
        game_state = self.create_test_game_state([
            ([Position(1, 10)], Direction.RIGHT)
        ])
        
        perception = Perception(game_state)
        snake = game_state.snakes[0]
        
        safe_dirs = perception.get_safe_immediate_directions(snake)
        
        assert Direction.LEFT not in safe_dirs  # Would hit wall
    
    def test_avoids_other_snakes(self):
        """Test avoids directions with other snakes"""
        # Two snakes adjacent
        game_state = self.create_test_game_state([
            ([Position(10, 10)], Direction.RIGHT),
            ([Position(11, 10)], Direction.LEFT)  # Directly to the right
        ])
        
        perception = Perception(game_state)
        snake = game_state.snakes[0]
        
        safe_dirs = perception.get_safe_immediate_directions(snake)
        
        assert Direction.RIGHT not in safe_dirs  # Would hit other snake
    
    def test_finds_nearest_food(self):
        """Test finds nearest food correctly"""
        game_state = self.create_test_game_state(
            [([Position(10, 10)], Direction.RIGHT)],
            food_positions=[Position(15, 10), Position(12, 10), Position(8, 8)]
        )
        
        perception = Perception(game_state)
        snake = game_state.snakes[0]
        
        nearest = perception.find_nearest_food(snake)
        
        assert nearest == Position(12, 10)  # Closest by Manhattan distance
    
    def test_predicts_danger_zones(self):
        """Test danger zone prediction"""
        game_state = self.create_test_game_state([
            ([Position(10, 10)], Direction.RIGHT),
            ([Position(15, 10)], Direction.LEFT)
        ])
        
        perception = Perception(game_state)
        snake = game_state.snakes[0]
        
        danger_zones = perception.predict_danger_zones(snake)
        
        # Should include positions other snake can move to
        assert Position(14, 10) in danger_zones  # Other snake can move here
        assert Position(15, 9) in danger_zones
        assert Position(15, 11) in danger_zones
        # Should include other snake's body
        assert Position(15, 10) in danger_zones


class TestSpaceEvaluator:
    """Tests for space evaluation"""
    
    def test_counts_reachable_space_correctly(self):
        """Test flood fill counts correct number of cells"""
        game_state = GameState(
            snakes=tuple(),
            food=frozenset(),
            width=10,
            height=10
        )
        
        evaluator = SpaceEvaluator(game_state)
        
        # Empty 8x8 grid (borders excluded)
        space = evaluator.count_reachable_space(
            Position(5, 5),
            obstacles=set(),
            max_depth=10
        )
        
        # Should count all cells in the grid
        assert space > 50  # At least 64 cells (8x8)
    
    def test_respects_obstacles(self):
        """Test flood fill respects obstacles"""
        game_state = GameState(
            snakes=tuple(),
            food=frozenset(),
            width=20,
            height=20
        )
        
        evaluator = SpaceEvaluator(game_state)
        
        # Create wall dividing space
        obstacles = {Position(10, y) for y in range(1, 19)}
        
        # Start on left side
        space = evaluator.count_reachable_space(
            Position(5, 10),
            obstacles=obstacles,
            max_depth=20
        )
        
        # Should only count left side (roughly half the grid)
        assert space < 180  # Less than full grid


class TestMoveSimulator:
    """Tests for move simulation"""
    
    def test_simulates_move_correctly(self):
        """Test simulating a single move"""
        snake = Snake(
            id=0,
            body=[Position(5, 5)],
            direction=Direction.RIGHT,
            personality=AIPersonality.BALANCED,
            color='test',
            symbol='T'
        )
        
        game_state = GameState(
            snakes=tuple([snake]),
            food=frozenset(),
            width=20,
            height=20
        )
        
        simulator = MoveSimulator(game_state)
        
        simulated = simulator.simulate_move(snake, Direction.UP)
        
        # Original snake unchanged
        assert snake.get_head() == Position(5, 5)
        assert snake.direction == Direction.RIGHT
        
        # Simulated snake moved
        assert simulated.get_head() == Position(5, 4)
        assert simulated.direction == Direction.UP
    
    def test_evaluates_death_negatively(self):
        """Test evaluation gives negative score for death"""
        # Snake at edge
        snake = Snake(
            id=0,
            body=[Position(1, 5)],
            direction=Direction.RIGHT,
            personality=AIPersonality.BALANCED,
            color='test',
            symbol='T'
        )
        
        game_state = GameState(
            snakes=tuple([snake]),
            food=frozenset(),
            width=20,
            height=20
        )
        
        simulator = MoveSimulator(game_state)
        
        # Evaluate moving into wall
        score = simulator.evaluate_future_state(snake, Direction.LEFT, depth=1)
        
        assert score < -500  # Heavily penalized


class TestStrategicEvaluator:
    """Tests for strategic evaluation"""
    
    def test_identifies_winning_position(self):
        """Test identifies when snake is winning"""
        snake1 = Snake(
            id=0,
            body=[Position(5, 5)],
            direction=Direction.RIGHT,
            personality=AIPersonality.BALANCED,
            color='test',
            symbol='T'
        )
        snake1.score = 100
        
        snake2 = Snake(
            id=1,
            body=[Position(10, 10)],
            direction=Direction.LEFT,
            personality=AIPersonality.BALANCED,
            color='test',
            symbol='T'
        )
        snake2.score = 30
        
        game_state = GameState(
            snakes=tuple([snake1, snake2]),
            food=frozenset(),
            width=20,
            height=20
        )
        
        evaluator = StrategicEvaluator(game_state)
        
        assert evaluator.should_play_defensively(snake1)
        assert not evaluator.should_play_defensively(snake2)
    
    def test_identifies_losing_position(self):
        """Test identifies when snake should take risks"""
        snake1 = Snake(
            id=0,
            body=[Position(5, 5)],
            direction=Direction.RIGHT,
            personality=AIPersonality.BALANCED,
            color='test',
            symbol='T'
        )
        snake1.score = 30
        
        snake2 = Snake(
            id=1,
            body=[Position(10, 10)],
            direction=Direction.LEFT,
            personality=AIPersonality.BALANCED,
            color='test',
            symbol='T'
        )
        snake2.score = 100
        
        game_state = GameState(
            snakes=tuple([snake1, snake2]),
            food=frozenset(),
            width=20,
            height=20
        )
        
        evaluator = StrategicEvaluator(game_state)
        
        assert evaluator.should_take_risks(snake1)
        assert not evaluator.should_take_risks(snake2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])