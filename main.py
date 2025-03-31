import sys
import traceback

# Import the game function from our refactored module
from src.game import run_game

# Entry point for the application
if __name__ == '__main__':
    try:
        # Run the game loop
        run_game()
    except Exception as e:
        # Print any unhandled exceptions
        print(f"Error in main: {e}")
        traceback.print_exc()
        sys.exit(1)
    # Exit cleanly
    sys.exit(0)