"""
Simplified Gesture Game Hub - Intuitive Controls
Controls:
- Show 1-9 fingers: Select game number
- OPEN palm: Start selected game  
- FIST: Close current game / Back to menu
- Swipe gestures: Game actions
"""

import cv2
import pygame
import threading
import time
import sys
import os

# Add games directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'games'))

from gesture_controller import SimplifiedGestureController
from game_manager import GameCollection

class SimpleGestureHub:
    def __init__(self):
        """Initialize simplified game hub"""
        pygame.init()
        
        # Game collection
        self.game_collection = GameCollection()
        
        # Gesture controller
        self.gesture = SimplifiedGestureController()
        
        # Camera
        self.cap = None
        self.running = True
        
        # Display
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Simple Gesture Game Hub")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        
        # Game state
        self.in_menu = True
        self.selected_number = 1  # Default to game 1
        
        # Gesture state
        self.current_gesture = None
        self.current_number = None
        self.current_swipe = None
        
        # Debounce timers
        self.last_action_time = 0
        self.action_delay = 0.5  # 500ms
        
    def initialize_camera(self):
        """Initialize webcam"""
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Error: Could not open webcam")
            return False
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return True
    
    def gesture_detection_loop(self):
        """Thread for gesture detection"""
        while self.running and self.cap is not None:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            frame = cv2.flip(frame, 1)
            
            # Detect gestures
            gesture, number, swipe, annotated = self.gesture.detect_gestures(frame)
            
            # Update state
            self.current_gesture = gesture
            self.current_number = number
            self.current_swipe = swipe
            
            # Show camera feed
            cv2.imshow('Gesture Control', annotated)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.running = False
                break
            
            time.sleep(0.033)
    
    def handle_gestures(self):
        """Handle simple gesture commands"""
        now = time.time()
        
        if now - self.last_action_time < self.action_delay:
            return  # Debounce
        
        # Select game with number gesture (1-9)
        if self.current_number and 1 <= self.current_number <= 9:
            self.selected_number = self.current_number
            self.last_action_time = now
            print(f"Selected Game: {self.selected_number}")
            time.sleep(0.3)  # Small delay
        
        # OPEN palm: Start game
        if self.current_gesture == "OPEN_PALM" and self.in_menu:
            game_name = self.get_game_name(self.selected_number)
            if game_name:
                print(f"Starting {game_name}...")
                self.game_collection.start_game(game_name)
                self.in_menu = False
                self.last_action_time = now
        
        # FIST: Close game / Back to menu
        if self.current_gesture == "FIST" and not self.in_menu:
            print("Closing game...")
            self.game_collection.stop_current_game()
            self.in_menu = True
            self.last_action_time = now
        
        # Pass swipe to current game
        if not self.in_menu and self.current_swipe:
            current_game = self.game_collection.get_current_game()
            if current_game:
                # For Fruit Slice game, use horizontal swipes
                if self.game_collection.current_game_name == "fruit_slice":
                    if self.current_swipe in ["LEFT", "RIGHT"]:
                        current_game.handle_swipe(self.current_swipe)
                else:
                    # For other games, use all swipes
                    current_game.handle_swipe(self.current_swipe)
    
    def get_game_name(self, number):
        """Get game name by number"""
        games = [
            "snake",    # 1
            "pong",     # 2
            "runner",   # 3
            "maze",     # 4
            "arkanoid", # 5
            "flappy",   # 6
            "space_invaders",  # 7
            "tetris",   # 8
            "fruit_slice"      # 9
        ]
        return games[number-1] if 1 <= number <= 9 else None
    
    def draw_menu(self):
        """Draw simple menu"""
        self.screen.fill((20, 20, 40))
        
        # Title
        title = self.font.render("SIMPLE GESTURE GAME HUB", True, (255, 255, 0))
        self.screen.blit(title, (400 - title.get_width()//2, 50))
        
        # Instructions
        inst_font = pygame.font.Font(None, 24)
        instructions = [
            "CONTROLS:",
            "• Show 1-9 fingers: Select game",
            "• OPEN palm: Start selected game",
            "• FIST: Close game / Back to menu",
            "• Swipe: Game actions",
            "• Press ESC to quit"
        ]
        
        for i, text in enumerate(instructions):
            text_surf = inst_font.render(text, True, (200, 200, 200))
            self.screen.blit(text_surf, (50, 120 + i * 30))
        
        # Game list
        game_names = [
            "1. Snake Game",
            "2. Pong Game", 
            "3. Runner Game",
            "4. Maze Game",
            "5. Arkanoid Game",
            "6. Flappy Game",
            "7. Space Invaders",
            "8. Tetris Game",
            "9. Fruit Slice"
        ]
        
        for i, game_text in enumerate(game_names):
            color = (0, 200, 255) if i+1 == self.selected_number else (150, 150, 150)
            text = self.font.render(game_text, True, color)
            self.screen.blit(text, (400 - text.get_width()//2, 300 + i * 40))
        
        # Selected game info
        if self.selected_number:
            game_name = self.get_game_name(self.selected_number)
            if game_name:
                selected_text = inst_font.render(f"Selected: Game {self.selected_number} - {game_name.title()}", 
                                               True, (100, 255, 100))
                self.screen.blit(selected_text, (400 - selected_text.get_width()//2, 550))
        
        pygame.display.flip()
    
    def run(self):
        """Main game loop"""
        if not self.initialize_camera():
            print("Failed to initialize camera")
            return
        
        # Start gesture thread
        gesture_thread = threading.Thread(target=self.gesture_detection_loop, daemon=True)
        gesture_thread.start()
        
        print("=" * 60)
        print("SIMPLE GESTURE GAME HUB")
        print("=" * 60)
        print("\nCONTROLS:")
        print("• Show 1-9 fingers: Select game")
        print("• OPEN palm: Start selected game")
        print("• FIST: Close game / Back to menu")
        print("• Swipe: Game actions")
        print("• Horizontal swipe: Slice fruits (Game 9)")
        print("• Press ESC: Quit")
        print("=" * 60)
        
        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, 
                                      pygame.K_4, pygame.K_5, pygame.K_6,
                                      pygame.K_7, pygame.K_8, pygame.K_9]:
                        self.selected_number = event.key - pygame.K_0
                    elif event.key == pygame.K_SPACE and self.in_menu:
                        # Space to start selected game
                        game_name = self.get_game_name(self.selected_number)
                        if game_name:
                            self.game_collection.start_game(game_name)
                            self.in_menu = False
        
            # Handle gestures
            self.handle_gestures()
            
            if self.in_menu:
                # Draw menu
                self.draw_menu()
            else:
                # Update and draw current game
                current_game = self.game_collection.get_current_game()
                if current_game:
                    current_game.update()
                    
                    # Draw game
                    game_surface = current_game.get_surface()
                    if game_surface:
                        self.screen.blit(game_surface, (0, 0))
                    else:
                        current_game.draw(self.screen)
                    
                    # Draw overlay with controls
                    overlay_font = pygame.font.Font(None, 24)
                    controls_text = overlay_font.render("Show FIST to return to menu", 
                                                       True, (255, 255, 0))
                    self.screen.blit(controls_text, 
                                   (400 - controls_text.get_width()//2, 10))
                    
                    pygame.display.flip()
            
            self.clock.tick(60)
        
        self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        print("\nClosing...")
        self.running = False
        
        if self.cap:
            self.cap.release()
        
        cv2.destroyAllWindows()
        self.game_collection.cleanup()
        pygame.quit()
        print("Game hub closed.")


def main():
    """Entry point"""
    try:
        hub = SimpleGestureHub()
        hub.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()