"""
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