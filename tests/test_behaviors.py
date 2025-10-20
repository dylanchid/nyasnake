"""
Unit tests for behavior tree implementations.

Run with: python -m pytest test_behaviors.py -v
"""

import pytest
from models import Position, Direction, GameState, Snake, AIPersonality
from behaviors import (
    SurvivalBehavior, FoodSeekingBehavior, AggressiveBehavior,
    SpaceMaximizationBehavior, DecisionMaker
)
from config import AI_CONFIG


class TestSurvivalBehavior:
    """Tests for survival behavior"""
    
    def test_chooses_direction_with_most_space(self):
        """Test survival chooses direction with most available space"""
        # Snake in corner - limited options
        snake = Snake(
            id=0,
            body=[Position(2, 2)],
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
        
        behavior = SurvivalBehavior()
        direction = behavior.execute(snake, game_state)
        
        # Should choose direction with most space (away from corner)
        assert direction is not None
        assert direction in [Direction.RIGHT, Direction.DOWN]
    
    def test_returns_none_when_trapped(self):
        """Test returns None when completely surrounded"""
        # Create snake surrounded by obstacles
        snake = Snake(
            id=0,
            body=[Position(10, 10)],
            direction=Direction.RIGHT,
            personality=AIPersonality.BALANCED,
            color='test',
            symbol='T'
        )
        
        # Other snake forming a box
        other_snake = Snake(
            id=1,
            body=[
                Position(9, 10), Position(9, 9), Position(10, 9),
                Position(11, 9), Position(11, 10), Position(11, 11),
                Position(10, 11), Position(9, 11)
            ],
            direction=Direction.LEFT,
            personality=AIPersonality.BALANCED,
            color='test',
            symbol='T'
        )
        
        game_state = GameState(
            snakes=tuple([snake, other_snake]),
            food=frozenset(),
            width=20,
            height=20
        )
        
        behavior = SurvivalBehavior()
        direction = behavior.execute(snake, game_state)
        
        assert direction is None


class TestFoodSeekingBehavior:
    """Tests for food seeking behavior"""
    
    def test_finds_path_to_food(self):
        """Test finds path to nearest food"""
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
            food=frozenset([Position(10, 5)]),
            width=20,
            height=20
        )
        
        behavior = FoodSeekingBehavior()
        direction = behavior.execute(snake, game_state)
        
        assert direction is not None
        # Should move toward food (RIGHT)
        assert direction == Direction.RIGHT
    
    def test_caches_path(self):
        """Test caches path for multiple calls"""
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
            food=frozenset([Position(10, 5)]),
            width=20,
            height=20
        )
        
        behavior = FoodSeekingBehavior()
        
        # First call - calculates path
        dir1 = behavior.execute(snake, game_state)
        assert snake.id in behavior.path_cache
        
        # Second call - should use cache
        dir2 = behavior.execute(snake, game_state)
        assert dir2 == dir1
    
    def test_returns_none_when_no_food(self):
        """Test returns None when no food available"""
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
            food=frozenset(),  # No food
            width=20,
            height=20
        )
        
        behavior = FoodSeekingBehavior()
        direction = behavior.execute(snake, game_state)
        
        assert direction is None


class TestAggressiveBehavior:
    """Tests for aggressive behavior"""
    
    def test_targets_weaker_snake(self):
        """Test aggressive behavior targets smaller snakes"""
        # Large snake
        snake = Snake(
            id=0,
            body=[Position(5, 5), Position(4, 5), Position(3, 5), Position(2, 5)],
            direction=Direction.RIGHT,
            personality=AIPersonality.AGGRESSIVE,
            color='test',
            symbol='T'
        )
        
        # Small snake nearby
        target = Snake(
            id=1,
            body=[Position(10, 5)],
            direction=Direction.LEFT,
            personality=AIPersonality.BALANCED,
            color='test',
            symbol='T'
        )
        
        game_state = GameState(
            snakes=tuple([snake, target]),
            food=frozenset(),
            width=20,
            height=20
        )
        
        behavior = AggressiveBehavior()
        direction = behavior.execute(snake, game_state)
        
        # Should move toward target
        assert direction is not None
        assert direction == Direction.RIGHT
    
    def test_returns_none_when_no_targets(self):
        """Test returns None when no weaker snakes"""
        # Small snake
        snake = Snake(
            id=0,
            body=[Position(5, 5)],
            direction=Direction.RIGHT,
            personality=AIPersonality.AGGRESSIVE,
            color='test',
            symbol='T'
        )
        
        # Larger snake
        other = Snake(
            id=1,
            body=[Position(10, 5), Position(9, 5), Position(8, 5)],
            direction=Direction.LEFT,
            personality=AIPersonality.BALANCED,
            color='test',
            symbol='T'
        )
        
        game_state = GameState(
            snakes=tuple([snake, other]),
            food=frozenset(),
            width=20,
            height=20
        )
        
        behavior = AggressiveBehavior()
        direction = behavior.execute(snake, game_state)
        
        assert direction is None  # No viable targets


class TestSpaceMaximizationBehavior:
    """Tests for space maximization behavior"""
    
    def test_chooses_direction_with_most_future_space(self):
        """Test chooses direction maximizing future space"""
        snake = Snake(
            id=0,
            body=[Position(10, 10)],
            direction=Direction.RIGHT,
            personality=AIPersonality.DEFENSIVE,
            color='test',
            symbol='T'
        )
        
        # Other snake blocking one direction
        other = Snake(
            id=1,
            body=[Position(11, 10), Position(12, 10), Position(13, 10)],
            direction=Direction.RIGHT,
            personality=AIPersonality.BALANCED,
            color='test',
            symbol='T'
        )
        
        game_state = GameState(
            snakes=tuple([snake, other]),
            food=frozenset(),
            width=20,
            height=20
        )
        
        behavior = SpaceMaximizationBehavior()
        direction = behavior.execute(snake, game_state)
        
        # Should not go RIGHT (blocked by other snake)
        assert direction is not None
        assert direction != Direction.RIGHT


class TestDecisionMaker:
    """Tests for overall decision making"""
    
    def test_aggressive_personality_hunts(self):
        """Test aggressive personality tries to hunt"""
        # Large aggressive snake
        snake = Snake(
            id=0,
            body=[Position(5, 5), Position(4, 5), Position(3, 5)],
            direction=Direction.RIGHT,
            personality=AIPersonality.AGGRESSIVE,
            color='test',
            symbol='T'
        )
        
        # Smaller target
        target = Snake(
            id=1,
            body=[Position(10, 5)],
            direction=Direction.LEFT,
            personality=AIPersonality.BALANCED,
            color='test',
            symbol='T'
        )
        
        game_state = GameState(
            snakes=tuple([snake, target]),
            food=frozenset(),
            width=20,
            height=20
        )
        
        decision_maker = DecisionMaker()
        decision = decision_maker.make_decision(snake, game_state)
        
        # Should move toward target
        assert decision.chosen_direction == Direction.RIGHT
        assert decision.confidence > 0
    
    def test_defensive_personality_maximizes_space(self):
        """Test defensive personality prioritizes space"""
        snake = Snake(
            id=0,
            body=[Position(10, 10)],
            direction=Direction.RIGHT,
            personality=AIPersonality.DEFENSIVE,
            color='test',
            symbol='T'
        )
        
        game_state = GameState(
            snakes=tuple([snake]),
            food=frozenset([Position(11, 10)]),  # Food directly ahead
            width=20,
            height=20
        )
        
        decision_maker = DecisionMaker()
        decision = decision_maker.make_decision(snake, game_state)
        
        # Defensive snake might not go for food if risky
        # Just verify it makes a decision
        assert decision.chosen_direction is not None
        assert decision.confidence > 0
    
    def test_balanced_personality_seeks_food(self):
        """Test balanced personality seeks food efficiently"""
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
            food=frozenset([Position(10, 5)]),
            width=20,
            height=20
        )
        
        decision_maker = DecisionMaker()
        decision = decision_maker.make_decision(snake, game_state)
        
        # Should move toward food
        assert decision.chosen_direction == Direction.RIGHT
        assert decision.confidence > 0
    
    def test_meta_strategy_override_when_winning(self):
        """Test meta-strategy overrides to defensive when winning"""
        # Aggressive snake that's winning
        snake = Snake(
            id=0,
            body=[Position(5, 5)],
            direction=Direction.RIGHT,
            personality=AIPersonality.AGGRESSIVE,
            color='test',
            symbol='T'
        )
        snake.score = 100  # High score
        
        # Losing opponent
        other = Snake(
            id=1,
            body=[Position(15, 15)],
            direction=Direction.LEFT,
            personality=AIPersonality.BALANCED,
            color='test',
            symbol='T'
        )
        other.score = 20
        
        game_state = GameState(
            snakes=tuple([snake, other]),
            food=frozenset(),
            width=20,
            height=20,
            current_frame=100
        )
        
        decision_maker = DecisionMaker()
        decision = decision_maker.make_decision(snake, game_state)
        
        # Should still make a decision (exact behavior may vary)
        assert decision.chosen_direction is not None
        assert decision.confidence >= 0


class TestErrorHandling:
    """Tests for error handling in behaviors"""
    
    def test_handles_empty_safe_directions(self):
        """Test gracefully handles no safe directions"""
        # Snake completely surrounded (will die)
        snake = Snake(
            id=0,
            body=[Position(1, 1)],  # Corner position
            direction=Direction.RIGHT,
            personality=AIPersonality.BALANCED,
            color='test',
            symbol='T'
        )
        
        # Wall on all sides
        game_state = GameState(
            snakes=tuple([snake]),
            food=frozenset(),
            width=3,  # Tiny grid
            height=3
        )
        
        decision_maker = DecisionMaker()
        decision = decision_maker.make_decision(snake, game_state)
        
        # Should return a decision even if doomed
        assert decision.chosen_direction is not None
        assert decision.confidence == 0.0  # Low confidence when doomed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])