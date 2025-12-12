"""
Setup for Simple Gesture Games
"""

import os

def create_simple_files():
    """Create simplified game files"""
    
    # Create simplified gesture controller
    gesture_content = '''"""
Simplified Gesture Controller - Intuitive Number & Action Gestures
"""

import cv2
import mediapipe as mp
import numpy as np
from collections import deque

class SimplifiedGestureController:
    def __init__(self):
        """Initialize simplified gesture detection"""
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Initialize hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,  # Allow two hands
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        # Gesture tracking
        self.gesture_history = deque(maxlen=10)
        self.last_gesture = None
        self.last_number = None
        self.gesture_confidence = 0
        
        # For swipe detection
        self.prev_hand_pos = None
        self.swipe_threshold = 0.05
        
    def detect_gestures(self, frame):
        """
        Detect simple gestures: numbers 1-9 and basic actions
        Returns: (gesture_type, number, swipe_direction, annotated_frame)
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        annotated = frame.copy()
        
        # Default values
        gesture_type = None
        number = None
        swipe_direction = None
        
        # Process hands
        results = self.hands.process(rgb_frame)
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw hand landmarks
                self.mp_drawing.draw_landmarks(
                    annotated, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2),
                    self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                )
                
                # Get hand center (wrist)
                wrist = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]
                current_pos = np.array([wrist.x, wrist.y])
                
                # Detect number gesture (extended fingers)
                extended_fingers = self._count_extended_fingers(hand_landmarks)
                number = extended_fingers if 1 <= extended_fingers <= 9 else None
                
                # Detect gesture type
                if extended_fingers == 0:
                    gesture_type = "FIST"
                elif extended_fingers == 5:
                    gesture_type = "OPEN_PALM"
                else:
                    gesture_type = "NUMBER"
                
                # Detect swipe
                if self.prev_hand_pos is not None:
                    movement = current_pos - self.prev_hand_pos
                    
                    if np.linalg.norm(movement) > self.swipe_threshold:
                        if abs(movement[0]) > abs(movement[1]):
                            swipe_direction = "RIGHT" if movement[0] > 0 else "LEFT"
                        else:
                            swipe_direction = "DOWN" if movement[1] > 0 else "UP"
                
                self.prev_hand_pos = current_pos
                
                # Display info
                if number:
                    cv2.putText(annotated, f"Number: {number}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                
                if gesture_type:
                    cv2.putText(annotated, f"Gesture: {gesture_type}", (10, 70),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                
                if swipe_direction:
                    cv2.putText(annotated, f"Swipe: {swipe_direction}", (10, 110),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        return gesture_type, number, swipe_direction, annotated
    
    def _count_extended_fingers(self, landmarks):
        """Count extended fingers (1-5)"""
        finger_tips = [
            self.mp_hands.HandLandmark.THUMB_TIP,
            self.mp_hands.HandLandmark.INDEX_FINGER_TIP,
            self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
            self.mp_hands.HandLandmark.RING_FINGER_TIP,
            self.mp_hands.HandLandmark.PINKY_TIP
        ]
        
        finger_mcp = [
            self.mp_hands.HandLandmark.THUMB_MCP,
            self.mp_hands.HandLandmark.INDEX_FINGER_MCP,
            self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP,
            self.mp_hands.HandLandmark.RING_FINGER_MCP,
            self.mp_hands.HandLandmark.PINKY_MCP
        ]
        
        extended = 0
        
        # Check fingers (skip thumb for now)
        for tip, mcp in zip(finger_tips[1:], finger_mcp[1:]):
            if landmarks.landmark[tip].y < landmarks.landmark[mcp].y:
                extended += 1
        
        # Check thumb (special case)
        thumb_tip = landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
        thumb_ip = landmarks.landmark[self.mp_hands.HandLandmark.THUMB_IP]
        
        # For right hand
        if landmarks.landmark[self.mp_hands.HandLandmark.WRIST].x < landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP].x:
            # Right hand
            if thumb_tip.x > thumb_ip.x:
                extended += 1
        else:
            # Left hand
            if thumb_tip.x < thumb_ip.x:
                extended += 1
        
        return extended
    
    def reset(self):
        """Reset gesture state"""
        self.gesture_history.clear()
        self.prev_hand_pos = None
        self.last_gesture = None
        self.last_number = None
'''
    
    with open("gesture_controller_simple.py", "w") as f:
        f.write(gesture_content)
    
    print("✓ Created simplified gesture controller")
    
    # Create simplified main file
    main_content = '''"""
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

from gesture_controller_simple import SimplifiedGestureController

class SimpleGame:
    """Simple placeholder game"""
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        self.score = 0
        self.game_over = False
        self.paused = False
    
    def handle_swipe(self, direction):
        """Handle swipe"""
        print(f"Game received swipe: {direction}")
    
    def update(self):
        """Update game"""
        pass
    
    def draw(self, surface=None):
        """Draw game"""
        target = surface or self.screen
        target.fill((0, 0, 0))
        font = pygame.font.Font(None, 48)
        text = font.render("Simple Game - Swipe to play!", True, (255, 255, 255))
        target.blit(text, (self.width//2 - text.get_width()//2, 
                          self.height//2 - text.get_height()//2))
        
        if surface is None:
            pygame.display.flip()
    
    def get_surface(self):
        """Get game surface"""
        surf = pygame.Surface((self.width, self.height))
        self.draw(surf)
        return surf

class SimpleGestureHub:
    def __init__(self):
        """Initialize simplified game hub"""
        pygame.init()
        
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
        self.selected_number = 1
        self.current_game = None
        
        # Gesture state
        self.current_gesture = None
        self.current_number = None
        self.current_swipe = None
        
        # Debounce
        self.last_action_time = 0
    
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
        
        if now - self.last_action_time < 0.5:
            return  # Debounce
        
        # Select game with number gesture
        if self.current_number and 1 <= self.current_number <= 9:
            self.selected_number = self.current_number
            self.last_action_time = now
            print(f"Selected Game: {self.selected_number}")
        
        # OPEN palm: Start game
        if self.current_gesture == "OPEN_PALM" and self.in_menu:
            print(f"Starting Game {self.selected_number}...")
            self.current_game = SimpleGame()
            self.in_menu = False
            self.last_action_time = now
        
        # FIST: Close game
        if self.current_gesture == "FIST" and not self.in_menu:
            print("Closing game...")
            self.current_game = None
            self.in_menu = True
            self.last_action_time = now
        
        # Pass swipe to current game
        if not self.in_menu and self.current_swipe and self.current_game:
            self.current_game.handle_swipe(self.current_swipe)
    
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
        
        # Selected info
        selected_text = inst_font.render(f"Selected: Game {self.selected_number}", 
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
        print("\\nCONTROLS:")
        print("• Show 1-9 fingers: Select game")
        print("• OPEN palm: Start selected game")
        print("• FIST: Close game / Back to menu")
        print("• Swipe: Game actions")
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
                        self.current_game = SimpleGame()
                        self.in_menu = False
            
            # Handle gestures
            self.handle_gestures()
            
            if self.in_menu:
                self.draw_menu()
            else:
                if self.current_game:
                    self.current_game.update()
                    self.current_game.draw()
                    
                    # Draw overlay
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
        print("\\nClosing...")
        self.running = False
        
        if self.cap:
            self.cap.release()
        
        cv2.destroyAllWindows()
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
'''
    
    with open("main_simple.py", "w") as f:
        f.write(main_content)
    
    print("✓ Created simplified main game hub")
    print("\n" + "="*50)
    print("SETUP COMPLETE!")
    print("="*50)
    print("\nTo run the simplified gesture game hub:")
    print("  python main_simple.py")
    print("\nControls:")
    print("  1. Show 1-9 fingers to select game")
    print("  2. OPEN palm to start game")
    print("  3. FIST to close game / back to menu")
    print("  4. Swipe gestures for game actions")
    print("  5. Horizontal swipes for Fruit Slice")

if __name__ == "__main__":
    create_simple_files()