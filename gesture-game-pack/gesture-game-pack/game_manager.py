"""
Game Manager for 9 Unique Games
"""

import pygame
import importlib
import os

class GameCollection:
    def __init__(self):
        """Initialize collection of 9 games"""
        self.games = {
            'snake': 'games.snake_game.SnakeGame',
            'pong': 'games.pong_game.PongGame',
            'runner': 'games.runner_game.RunnerGame',
            'maze': 'games.maze_game.MazeGame',
            'arkanoid': 'games.arkanoid_game.ArkanoidGame',
            'flappy': 'games.flappy_game.FlappyGame',
            'space_invaders': 'games.space_invaders.SpaceInvaders',
            'tetris': 'games.tetris_game.TetrisGame',
            'fruit_slice': 'games.fruit_slice.FruitSliceGame'
        }
        
        self.current_game = None
        self.current_game_name = None
        
        # Load all game modules
        self.game_modules = {}
        self._load_all_games()
    
    def _load_all_games(self):
        """Dynamically import all game modules"""
        for game_name, game_path in self.games.items():
            try:
                module_name, class_name = game_path.rsplit('.', 1)
                module = importlib.import_module(module_name)
                game_class = getattr(module, class_name)
                self.game_modules[game_name] = game_class
                print(f"✓ Loaded: {game_name}")
            except Exception as e:
                print(f"✗ Failed to load {game_name}: {e}")
    
    def start_game(self, game_name):
        """Start a specific game"""
        if game_name in self.game_modules:
            self.current_game = self.game_modules[game_name]()
            self.current_game_name = game_name
            return True
        return False
    
    def stop_current_game(self):
        """Stop the current game"""
        if self.current_game:
            self.current_game.cleanup()
            self.current_game = None
            self.current_game_name = None
    
    def get_current_game(self):
        """Get current game instance"""
        return self.current_game
    
    def get_controls(self, game_name):
        """Get control instructions for a game"""
        controls = {
            'snake': [
                "Swipe: Change direction",
                "Pinch: Speed boost",
                "Open palm: Pause"
            ],
            'pong': [
                "Swipe UP/DOWN: Move paddle",
                "Pinch: Power shot",
                "Open palm: Pause"
            ],
            'runner': [
                "Swipe UP: Jump",
                "Swipe DOWN: Slide",
                "Swipe LEFT/RIGHT: Change lanes",
                "Pinch: Speed boost"
            ],
            'maze': [
                "Swipe: Move through maze",
                "Pinch: Use map",
                "Open palm: Hint"
            ],
            'arkanoid': [
                "Swipe LEFT/RIGHT: Move paddle",
                "Pinch: Launch ball",
                "Open palm: Pause"
            ],
            'flappy': [
                "Swipe UP: Flap wings",
                "Pinch: Power flap",
                "Open palm: Pause"
            ],
            'space_invaders': [
                "Swipe LEFT/RIGHT: Move ship",
                "Swipe UP: Shoot",
                "Pinch: Power weapon",
                "Open palm: Shield"
            ],
            'tetris': [
                "Swipe LEFT/RIGHT: Move piece",
                "Swipe UP: Rotate",
                "Swipe DOWN: Soft drop",
                "Pinch: Hard drop"
            ],
            'fruit_slice': [
                "Swipe: Slice fruits",
                "Pinch: Power slice",
                "Open palm: Pause"
            ]
        }
        return controls.get(game_name, [])
    
    def cleanup(self):
        """Clean up all games"""
        self.stop_current_game()


# Base Game Interface
class BaseGame:
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        self.running = True
        self.paused = False
        self.score = 0
        self.game_over = False
        
    def handle_swipe(self, direction):
        """Handle swipe gesture (to be overridden by games)"""
        pass
    
    def handle_gesture(self, gesture_data):
        """Handle gesture input (to be overridden)"""
        pass
    
    def update(self):
        """Update game state (to be overridden)"""
        pass
    
    def draw(self, surface=None):
        """Draw game (to be overridden)"""
        pass
    
    def get_surface(self):
        """Get game surface (for rendering in hub)"""
        return None
    
    def cleanup(self):
        """Clean up game resources"""
        pass