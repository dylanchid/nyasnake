"""
Main entry point for the Advanced Snake AI Battle.

Usage:
    python main.py
    python main.py --debug
    python main.py --log-level DEBUG
"""

import asyncio
import sys
import logging
import argparse

from game import Game
from config import AI_CONFIG, DEBUG_CONFIG


def setup_logging(log_level: str = "INFO"):
    """Configure logging for the application"""
    # Create formatters
    console_formatter = logging.Formatter(
        '%(levelname)-8s [%(name)s] %(message)s'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)-8s - [%(name)s:%(funcName)s:%(lineno)d] - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.WARNING)  # Only warnings/errors to console during game
    
    # File handler
    file_handler = logging.FileHandler('snake_ai.log', mode='w')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Log startup
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("Advanced Snake AI Battle - Logging Initialized")
    logger.info(f"Log Level: {log_level}")
    logger.info("="*60)


async def main():
    """Main entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Advanced Snake AI Battle')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug visualization')
    parser.add_argument('--log-level', type=str, default=DEBUG_CONFIG.LOG_LEVEL,
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Set logging level')
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Override debug config if flag set
    if args.debug:
        from config import DebugConfig
        global DEBUG_CONFIG
        DEBUG_CONFIG = DebugConfig(
            SHOW_DANGER_ZONES=True,
            SHOW_PATHS=True,
            SHOW_EVALUATION_SCORES=False,
            LOG_DECISIONS=True,
            LOG_LEVEL=args.log_level
        )
    
    print("=" * 60)
    print("🐍 ADVANCED SNAKE AI BATTLE 🐍")
    print("=" * 60)
    print("\n✨ Production-Quality Implementation ✨\n")
    
    print("🎯 Advanced Features:")
    print("  • TRUE Recursive Look-Ahead (depth={})".format(AI_CONFIG.SIMULATION_DEPTH))
    print("  • Temporal A* Pathfinding (moving obstacles)")
    print("  • Probabilistic Opponent Prediction")
    print("  • Temporal Space Evaluation")
    print("  • Behavior Trees with Personalities")
    print("  • Strategic Risk/Reward Evaluation")
    print("  • Synchronized Decision Making")
    print("  • Comprehensive Logging & Error Handling")
    
    print("\n🤖 Three AI Personalities:")
    print("  🔴 AGGRESSIVE  - Hunts weaker snakes, takes risks")
    print("  🟢 DEFENSIVE   - Maximizes space, avoids danger")
    print("  🔵 BALANCED    - Optimal pathfinding, calculated risks")
    
    print("\n🔧 Configuration:")
    print(f"  • Simulation Depth: {AI_CONFIG.SIMULATION_DEPTH} moves")
    print(f"  • Flood Fill Depth: {AI_CONFIG.FLOOD_FILL_MAX_DEPTH} cells")
    print(f"  • Path Caching: {AI_CONFIG.PATH_CACHE_DURATION} frames")
    print(f"  • A* Node Limit: {AI_CONFIG.ASTAR_MAX_NODES} nodes")
    print(f"  • Prediction Depth: {AI_CONFIG.PREDICTION_DEPTH} steps")
    
    print("\n📊 New Features in This Version:")
    print("  ✅ Probabilistic opponent movement prediction")
    print("  ✅ Temporal space evaluation with occupation probability")
    print("  ✅ Meta-strategy overrides (defensive when winning)")
    print("  ✅ Comprehensive error handling")
    print("  ✅ Detailed logging to snake_ai.log")
    print("  ✅ Debug visualization (use --debug flag)")
    
    if args.debug:
        print("\n🐛 DEBUG MODE ENABLED")
        print("  • Danger zones will be shown in magenta (×)")
        print("  • Cached paths will be shown in cyan (·)")
        print("  • Decision reasoning will be displayed")
    
    print("\n" + "=" * 60)
    print("Starting simulation in 3 seconds...")
    print("Check snake_ai.log for detailed decision logs")
    print("=" * 60 + "\n")
    
    await asyncio.sleep(3)
    
    # Create and run game
    game = Game()
    
    try:
        logger.info("Starting game simulation")
        await game.game_loop()
    except KeyboardInterrupt:
        logger.info("Game interrupted by user")
        print("\n\n⚠️  Simulation interrupted by user")
        return
    except Exception as e:
        logger.error(f"Game crashed: {e}", exc_info=True)
        print(f"\n\n❌ Game crashed: {e}")
        print("Check snake_ai.log for details")
        return
    
    print("\n" + "=" * 60)
    print("✅ SIMULATION COMPLETE")
    print("=" * 60)
    
    # Print final statistics
    print("\n📊 Final Statistics:")
    for snake in game.snakes:
        personality = {
            0: "AGGRESSIVE",
            1: "DEFENSIVE", 
            2: "BALANCED"
        }[snake.id]
        
        status = "🏆 WINNER" if snake.alive else "💀 Eliminated"
        print(f"  {snake.color}{personality:11} - {status:13} | "
              f"Score: {snake.score:4} | "
              f"Length: {snake.get_length():3} | "
              f"Kills: {snake.kills}\033[0m")
    
    print("\n📝 Detailed logs saved to: snake_ai.log")
    print("=" * 60)
    
    logger.info("Program completed successfully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)