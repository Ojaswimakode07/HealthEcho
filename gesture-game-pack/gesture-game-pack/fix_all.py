"""
Fix all gesture game issues
"""

import os

print("Fixing gesture game issues...")
print("-" * 50)

# 1. Create fixed gesture controller
gesture_code = '''"""
Fixed Gesture Controller - One Hand for 1-9 + Better Detection
"""

import cv2
import mediapipe as mp
import numpy as np
from collections import deque

class FixedGestureController:
    def __init__(self):
        """Initialize fixed gesture detection"""
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Initialize hands - track both hands for numbers 6-9
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,  # Allow two hands for numbers 6-9
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        # Gesture tracking
        self.prev_hand_pos = None
        self.swipe_threshold = 0.04
        self.swipe_history = deque(maxlen=5)
        
        # For number detection
        self.number_history = deque(maxlen=10)
        self.stable_number = None
        
        # For pinch detection
        self.pinch_threshold = 0.05
        
    def detect_gestures(self, frame):
        """
        Detect gestures including numbers 1-9 with one/two hands
        Returns: (gesture_type, number, swipe_direction, is_pinching, annotated_frame)
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        annotated = frame.copy()
        
        # Default values
        gesture_type = None
        number = None
        swipe_direction = None
        is_pinching = False
        
        # Process hands
        results = self.hands.process(rgb_frame)
        
        if results.multi_hand_landmarks:
            hand_count = len(results.multi_hand_landmarks)
            total_fingers = 0
            current_pos = None
            
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw hand landmarks
                self.mp_drawing.draw_landmarks(
                    annotated, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2),
                    self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                )
                
                # Get hand center (wrist)
                wrist = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]
                if current_pos is None:
                    current_pos = np.array([wrist.x, wrist.y])
                
                # Count extended fingers for this hand
                fingers = self._count_extended_fingers(hand_landmarks)
                total_fingers += fingers
                
                # Detect pinch (thumb + index)
                is_pinching = self._detect_pinch(hand_landmarks)
                if is_pinching:
                    gesture_type = "PINCH"
                
                # Detect swipe
                swipe_dir = self._detect_swipe(current_pos)
                if swipe_dir:
                    swipe_direction = swipe_dir
                    gesture_type = "SWIPE"
            
            # Determine number (1-9)
            if 1 <= total_fingers <= 9:
                number = total_fingers
                self.number_history.append(number)
                
                # Get most common number from history (for stability)
                if len(self.number_history) >= 5:
                    from collections import Counter
                    most_common = Counter(self.number_history).most_common(1)
                    if most_common:
                        self.stable_number = most_common[0][0]
                        number = self.stable_number
                
                gesture_type = "NUMBER"
            
            # Detect fist (0 fingers)
            elif total_fingers == 0:
                gesture_type = "FIST"
            
            # Detect open palm (10 fingers with both hands)
            elif total_fingers == 10:
                gesture_type = "OPEN_PALM"
            
            # Update position for next swipe detection
            if current_pos is not None:
                self.prev_hand_pos = current_pos
        
        # Display info
        y_offset = 30
        if number:
            cv2.putText(annotated, f"Number: {number}", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            y_offset += 40
        
        if gesture_type:
            cv2.putText(annotated, f"Gesture: {gesture_type}", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
            y_offset += 40
        
        if swipe_direction:
            cv2.putText(annotated, f"Swipe: {swipe_direction}", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            y_offset += 40
        
        if is_pinching:
            cv2.putText(annotated, "PINCHING", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 100, 100), 2)
        
        return gesture_type, number, swipe_direction, is_pinching, annotated
    
    def _count_extended_fingers(self, landmarks):
        """Count extended fingers (0-5 per hand)"""
        # Tips of fingers
        tips = [
            self.mp_hands.HandLandmark.THUMB_TIP,
            self.mp_hands.HandLandmark.INDEX_FINGER_TIP,
            self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
            self.mp_hands.HandLandmark.RING_FINGER_TIP,
            self.mp_hands.HandLandmark.PINKY_TIP
        ]
        
        # Reference points (MCP joints for fingers, IP for thumb)
        ref_points = [
            self.mp_hands.HandLandmark.THUMB_IP,  # For thumb
            self.mp_hands.HandLandmark.INDEX_FINGER_PIP,
            self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP,
            self.mp_hands.HandLandmark.RING_FINGER_PIP,
            self.mp_hands.HandLandmark.PINKY_PIP
        ]
        
        extended = 0
        
        # Check each finger
        for tip_idx, ref_idx in zip(tips, ref_points):
            tip = landmarks.landmark[tip_idx]
            ref = landmarks.landmark[ref_idx]
            
            # For thumb, check horizontal position
            if tip_idx == self.mp_hands.HandLandmark.THUMB_TIP:
                # Thumb is extended if it's away from hand
                if abs(tip.x - ref.x) > 0.1:
                    extended += 1
            else:
                # Other fingers: extended if tip is above reference point
                if tip.y < ref.y:
                    extended += 1
        
        return extended
    
    def _detect_pinch(self, landmarks):
        """Detect pinch gesture (thumb + index finger close)"""
        thumb_tip = landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
        index_tip = landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        
        # Calculate distance
        distance = np.sqrt((thumb_tip.x - index_tip.x)**2 + (thumb_tip.y - index_tip.y)**2)
        
        return distance < self.pinch_threshold
    
    def _detect_swipe(self, current_pos):
        """Detect swipe direction"""
        if self.prev_hand_pos is None:
            return None
        
        movement = current_pos - self.prev_hand_pos
        
        # Check if movement is significant
        if np.linalg.norm(movement) > self.swipe_threshold:
            # Add to history
            self.swipe_history.append(movement)
            
            # Average recent movements for smoother detection
            if len(self.swipe_history) >= 3:
                avg_movement = np.mean(self.swipe_history, axis=0)
                
                # Determine direction
                if abs(avg_movement[0]) > abs(avg_movement[1]):
                    return "RIGHT" if avg_movement[0] > 0 else "LEFT"
                else:
                    return "DOWN" if avg_movement[1] > 0 else "UP"
        
        return None
    
    def reset(self):
        """Reset gesture state"""
        self.prev_hand_pos = None
        self.swipe_history.clear()
        self.number_history.clear()
        self.stable_number = None
'''

with open("gesture_controller_fixed.py", "w") as f:
    f.write(gesture_code)
print("✓ Created fixed gesture controller")

# 2. Create main file
main_code = '''"""
Fixed Main Game Hub
Run this file: python main_fixed.py
"""

import cv2
import pygame
import threading
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'games'))

from gesture_controller_fixed import FixedGestureController

# Import your actual games here
# from snake_game import SnakeGame
# from pong_game import PongGame
# etc.

class SimpleGame:
    """Placeholder for your games"""
    def __init__(self, game_num):
        self.game_num = game_num
        self.width = 800
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.score = 0
        
    def handle_gesture(self, data):
        print(f"Game {self.game_num}: {data}")
        
    def update(self):
        pass
        
    def draw(self, surface=None):
        target = surface or self.screen
        target.fill((20, 20, 40))
        font = pygame.font.Font(None, 48)
        text = font.render(f"Game {self.game_num} Placeholder", True, (255, 255, 255))
        target.blit(text, (self.width//2 - text.get_width()//2, self.height//2 - 24))
        
        if surface is None:
            pygame.display.flip()
    
    def get_surface(self):
        surf = pygame.Surface((self.width, self.height))
        self.draw(surf)
        return surf

class FixedGameHub:
    def __init__(self):
        pygame.init()
        self.gesture = FixedGestureController()
        self.cap = None
        self.running = True
        self.width, self.height = 800, 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Fixed Gesture Game Hub")
        self.clock = pygame.time.Clock()
        
        self.in_menu = True
        self.selected_number = 1
        self.current_game = None
        
        # Game names
        self.games = {
            1: "Snake", 2: "Pong", 3: "Runner", 4: "Maze", 5: "Arkanoid",
            6: "Flappy", 7: "Space Invaders", 8: "Tetris", 9: "Fruit Slice"
        }
    
    def initialize_camera(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap or not self.cap.isOpened():
            print("Camera error - using keyboard only")
            return False
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return True
    
    def gesture_loop(self):
        while self.running and self.cap:
            ret, frame = self.cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            gesture, number, swipe, pinch, annotated = self.gesture.detect_gestures(frame)
            
            # Update state
            self.current_gesture = gesture
            self.current_number = number
            self.current_swipe = swipe
            self.is_pinching = pinch
            
            cv2.imshow('Gesture Control', annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.running = False
            time.sleep(0.033)
    
    def handle_gestures(self):
        # Select game
        if self.current_number and 1 <= self.current_number <= 9:
            self.selected_number = self.current_number
        
        # Start game
        if self.in_menu and (self.current_gesture in ["OPEN_PALM", "PINCH"] or self.is_pinching):
            print(f"Starting Game {self.selected_number}")
            self.current_game = SimpleGame(self.selected_number)
            self.in_menu = False
            time.sleep(0.5)
        
        # Return to menu
        if self.current_gesture == "FIST" and not self.in_menu:
            self.current_game = None
            self.in_menu = True
            time.sleep(0.5)
    
    def draw_menu(self):
        self.screen.fill((20, 20, 40))
        font = pygame.font.Font(None, 36)
        
        # Title
        title = font.render("GESTURE GAME HUB", True, (255, 255, 0))
        self.screen.blit(title, (self.width//2 - title.get_width()//2, 30))
        
        # Instructions
        small = pygame.font.Font(None, 24)
        lines = [
            "SELECT GAME: Show 1-9 fingers (use both hands for 6-9)",
            "START: OPEN palm or PINCH",
            "RETURN: FIST",
            "QUIT: Press ESC or Q in camera window"
        ]
        
        for i, line in enumerate(lines):
            text = small.render(line, True, (200, 200, 255))
            self.screen.blit(text, (50, 100 + i * 30))
        
        # Game grid
        for num in range(1, 10):
            row = (num - 1) // 3
            col = (num - 1) % 3
            x = 200 + col * 150
            y = 250 + row * 100
            
            # Box
            color = (0, 150, 255) if num == self.selected_number else (50, 50, 80)
            pygame.draw.rect(self.screen, color, (x, y, 120, 80), border_radius=10)
            pygame.draw.rect(self.screen, (100, 100, 150), (x, y, 120, 80), 2, border_radius=10)
            
            # Number
            num_text = font.render(str(num), True, (255, 255, 255))
            self.screen.blit(num_text, (x + 60 - num_text.get_width()//2, y + 20))
            
            # Game name
            name_text = small.render(self.games[num], True, (200, 200, 200))
            self.screen.blit(name_text, (x + 60 - name_text.get_width()//2, y + 50))
        
        # Selected
        selected = small.render(f"Selected: Game {self.selected_number} - {self.games[self.selected_number]}", 
                              True, (100, 255, 100))
        self.screen.blit(selected, (self.width//2 - selected.get_width()//2, 550))
        
        pygame.display.flip()
    
    def run(self):
        cam_ok = self.initialize_camera()
        
        if cam_ok:
            thread = threading.Thread(target=self.gesture_loop, daemon=True)
            thread.start()
            print("Camera started - using gesture controls")
        else:
            print("Camera not available - using keyboard only")
        
        print("\\nCONTROLS:")
        print("• Keyboard 1-9: Select game")
        print("• SPACE: Start game")
        print("• ESC: Quit")
        if cam_ok:
            print("• Gestures: Numbers 1-9, OPEN palm/PINCH to start, FIST to return")
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        self.selected_number = event.key - pygame.K_0
                    elif event.key == pygame.K_SPACE and self.in_menu:
                        self.current_game = SimpleGame(self.selected_number)
                        self.in_menu = False
            
            if cam_ok:
                self.handle_gestures()
            
            if self.in_menu:
                self.draw_menu()
            else:
                if self.current_game:
                    self.current_game.update()
                    self.current_game.draw()
                    
                    # Return hint
                    hint = pygame.font.Font(None, 24).render("Show FIST to return to menu", 
                                                           True, (255, 255, 0))
                    self.screen.blit(hint, (self.width//2 - hint.get_width()//2, 10))
                    pygame.display.flip()
            
            self.clock.tick(60)
        
        # Cleanup
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        pygame.quit()
        print("Game closed")

if __name__ == "__main__":
    hub = FixedGameHub()
    hub.run()
'''

with open("main_fixed.py", "w") as f:
    f.write(main_code)
print("✓ Created main_fixed.py")

print("\\n" + "-" * 50)
print("FIXES APPLIED!")
print("-" * 50)
print("\\nTo run the fixed version:")
print("1. Copy your game files to 'games/' folder")
print("2. Run: python main_fixed.py")
print("\\nFor 6-9 with one hand:")
print("• Use keyboard 6-9")
print("• OR use both hands (left:1-5 + right:1-4)")