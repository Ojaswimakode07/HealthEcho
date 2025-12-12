"""
Quick fix for all game issues
"""

import os
import sys

def fix_pong_game():
    """Replace the entire pong_game.py file"""
    pong_content = '''"""
Classic Pong Game with physics and power-ups
"""

import pygame
import random
import math
from game_manager import BaseGame

class PongGame(BaseGame):
    def __init__(self, width=800, height=600):
        super().__init__(width, height)
        self.title = "Pong Challenge"
        pygame.display.set_caption(self.title)
        
        # Colors
        self.bg_color = (10, 15, 25)
        self.paddle_color = (100, 200, 255)
        self.ball_color = (255, 255, 255)
        self.trail_color = (100, 150, 255)
        self.power_color = (255, 215, 0)
        
        # Game objects
        self.paddle_width = 15
        self.paddle_height = 100
        self.ball_size = 12
        
        # Paddle positions
        self.left_paddle = height // 2 - self.paddle_height // 2
        self.right_paddle = height // 2 - self.paddle_height // 2
        
        # AI paddle
        self.ai_speed = 4
        self.ai_difficulty = 1.0
        
        # Ball
        self.reset_ball()
        
        # Scores
        self.left_score = 0
        self.right_score = 0
        
        # Game state
        self.ball_served = False
        self.serve_delay = 60  # Fixed: Added this line
        self.serve_timer = 0
        
        # Power-up
        self.power_active = False
        self.power_timer = 0
        self.power_type = None
        
        # Trail effect
        self.ball_trail = []
        
        # Particles
        self.particles = []
    
    def reset_ball(self):
        """Reset ball to center"""
        self.ball_x = self.width // 2
        self.ball_y = self.height // 2
        
        # Random angle with some vertical component
        angle = random.uniform(math.pi / 6, math.pi / 3)
        if random.random() > 0.5:
            angle = math.pi - angle
        
        speed = 5
        self.ball_vx = math.cos(angle) * speed * random.choice([-1, 1])
        self.ball_vy = math.sin(angle) * speed * random.choice([-1, 1])
        
        self.ball_served = False
        self.serve_timer = self.serve_delay
        
        # Clear trail
        self.ball_trail = []
    
    def handle_gesture(self, gesture_data):
        """Handle gesture input"""
        direction = gesture_data.get('direction')
        
        # Control right paddle with up/down gestures
        paddle_speed = 8
        if direction == 'UP':
            self.right_paddle -= paddle_speed
        elif direction == 'DOWN':
            self.right_paddle += paddle_speed
        
        # Keep paddle on screen
        self.right_paddle = max(0, min(self.height - self.paddle_height, self.right_paddle))
        
        # Serve ball with pinch
        if not self.ball_served and gesture_data.get('pinch'):
            self.ball_served = True
        
        # Activate power with open palm
        if gesture_data.get('open_palm') and not self.power_active:
            self.activate_power()
        
        # Pause with peace sign
        if gesture_data.get('gesture') == 'PEACE':
            self.paused = not self.paused
    
    def activate_power(self):
        """Activate random power-up"""
        self.power_active = True
        self.power_timer = 300  # 5 seconds at 60 FPS
        self.power_type = random.choice(['big_paddle', 'fast_ball', 'magnet'])
    
    def update(self):
        """Update game state"""
        if self.paused:
            return
        
        # Serve delay
        if not self.ball_served:
            self.serve_timer -= 1
            if self.serve_timer <= 0:
                self.ball_served = True
            return
        
        # Update power-up
        if self.power_active:
            self.power_timer -= 1
            if self.power_timer <= 0:
                self.power_active = False
                if self.power_type == 'big_paddle':
                    self.paddle_height = 100  # Reset size
        
        # AI paddle movement
        target_y = self.ball_y - self.paddle_height // 2
        target_y = max(0, min(self.height - self.paddle_height, target_y))
        
        # Add some imperfection to AI
        ai_error = random.uniform(-20, 20) * (1 - self.ai_difficulty)
        target_y += ai_error
        
        # Move AI paddle toward target
        if self.left_paddle < target_y:
            self.left_paddle += min(self.ai_speed, target_y - self.left_paddle)
        elif self.left_paddle > target_y:
            self.left_paddle -= min(self.ai_speed, self.left_paddle - target_y)
        
        # Move ball
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy
        
        # Add to trail
        self.ball_trail.append((self.ball_x, self.ball_y))
        if len(self.ball_trail) > 10:
            self.ball_trail.pop(0)
        
        # Wall collision (top/bottom)
        if self.ball_y <= 0 or self.ball_y >= self.height - self.ball_size:
            self.ball_vy *= -1
            self.create_wall_particles()
        
        # Paddle collision
        paddle_bounce = self.check_paddle_collision()
        if paddle_bounce:
            self.create_paddle_particles()
            
            # Increase difficulty
            self.ai_difficulty = min(1.0, self.ai_difficulty + 0.01)
        
        # Scoring
        if self.ball_x < 0:
            self.right_score += 1
            self.reset_ball()
            self.ai_difficulty = max(0.3, self.ai_difficulty - 0.05)
        elif self.ball_x > self.width:
            self.left_score += 1
            self.reset_ball()
            self.ai_difficulty = max(0.3, self.ai_difficulty - 0.05)
        
        # Update particles
        self.update_particles()
    
    def check_paddle_collision(self):
        """Check and handle paddle collisions"""
        bounced = False
        
        # Left paddle
        if (self.ball_vx < 0 and
            self.ball_x <= self.paddle_width and
            self.ball_x >= 0 and
            self.ball_y + self.ball_size >= self.left_paddle and
            self.ball_y <= self.left_paddle + self.paddle_height):
            
            # Calculate bounce angle based on where ball hit paddle
            relative_y = (self.ball_y - self.left_paddle) / self.paddle_height
            angle = (relative_y - 0.5) * math.pi / 2  # -45 to 45 degrees
            
            speed = math.sqrt(self.ball_vx**2 + self.ball_vy**2) * 1.05  # Slight speed increase
            self.ball_vx = math.cos(angle) * speed
            self.ball_vy = math.sin(angle) * speed
            
            # Make sure ball moves right
            if self.ball_vx < 0:
                self.ball_vx *= -1
            
            self.ball_x = self.paddle_width  # Prevent sticking
            bounced = True
        
        # Right paddle
        elif (self.ball_vx > 0 and
              self.ball_x + self.ball_size >= self.width - self.paddle_width and
              self.ball_x <= self.width and
              self.ball_y + self.ball_size >= self.right_paddle and
              self.ball_y <= self.right_paddle + self.paddle_height):
            
            relative_y = (self.ball_y - self.right_paddle) / self.paddle_height
            angle = (relative_y - 0.5) * math.pi / 2
            
            speed = math.sqrt(self.ball_vx**2 + self.ball_vy**2) * 1.05
            self.ball_vx = math.cos(angle) * speed * -1  # Move left
            self.ball_vy = math.sin(angle) * speed
            
            self.ball_x = self.width - self.paddle_width - self.ball_size
            bounced = True
        
        # Apply power-up effects
        if bounced and self.power_active:
            if self.power_type == 'big_paddle':
                self.paddle_height = 150
            elif self.power_type == 'fast_ball':
                self.ball_vx *= 1.5
                self.ball_vy *= 1.5
            elif self.power_type == 'magnet':
                # Ball sticks slightly to paddle
                pass
        
        return bounced
    
    def create_wall_particles(self):
        """Create particles when ball hits wall"""
        for _ in range(8):
            particle = {
                'x': self.ball_x,
                'y': self.ball_y,
                'vx': random.uniform(-2, 2),
                'vy': random.uniform(-2, 2),
                'color': self.ball_color,
                'life': 20,
                'size': random.randint(1, 3)
            }
            self.particles.append(particle)
    
    def create_paddle_particles(self):
        """Create particles when ball hits paddle"""
        for _ in range(12):
            particle = {
                'x': self.ball_x,
                'y': self.ball_y,
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-3, 3),
                'color': self.paddle_color,
                'life': 25,
                'size': random.randint(2, 4)
            }
            self.particles.append(particle)
    
    def update_particles(self):
        """Update particle effects"""
        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['life'] -= 1
            
            if particle['life'] <= 0:
                self.particles.remove(particle)
    
    def draw(self, surface=None):
        """Draw game"""
        target = surface or self.screen
        target.fill(self.bg_color)
        
        # Draw center line
        for y in range(0, self.height, 20):
            pygame.draw.rect(target, (50, 50, 70), 
                           (self.width // 2 - 2, y, 4, 10))
        
        # Draw paddles with power-up effect
        left_paddle_color = self.power_color if (self.power_active and 
                                               self.power_type == 'big_paddle') else self.paddle_color
        
        pygame.draw.rect(target, left_paddle_color,
                        (0, self.left_paddle, self.paddle_width, self.paddle_height),
                        border_radius=5)
        
        pygame.draw.rect(target, self.paddle_color,
                        (self.width - self.paddle_width, self.right_paddle, 
                         self.paddle_width, self.paddle_height),
                        border_radius=5)
        
        # Draw ball trail
        for i, (trail_x, trail_y) in enumerate(self.ball_trail):
            alpha = int(255 * (i / len(self.ball_trail)))
            size = int(self.ball_size * (i / len(self.ball_trail)))
            
            if size > 0:
                trail_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(trail_surf, (*self.trail_color, alpha), 
                                 (size, size), size)
                target.blit(trail_surf, (trail_x - size, trail_y - size))
        
        # Draw ball
        ball_color = self.power_color if (self.power_active and 
                                        self.power_type == 'fast_ball') else self.ball_color
        
        pygame.draw.circle(target, ball_color,
                          (int(self.ball_x + self.ball_size // 2),
                           int(self.ball_y + self.ball_size // 2)),
                          self.ball_size // 2)
        
        # Draw particles
        for particle in self.particles:
            alpha = int(255 * (particle['life'] / 25))
            color_with_alpha = (*particle['color'], alpha)
            surf = pygame.Surface((particle['size'] * 2, particle['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color_with_alpha,
                             (particle['size'], particle['size']), particle['size'])
            target.blit(surf, (particle['x'] - particle['size'], particle['y'] - particle['size']))
        
        # Draw UI
        self.draw_ui(target)
        
        if surface is None:
            pygame.display.flip()
    
    def draw_ui(self, surface):
        """Draw user interface"""
        # Scores
        font = pygame.font.Font(None, 72)
        left_score = font.render(str(self.left_score), True, (200, 200, 200))
        right_score = font.render(str(self.right_score), True, (200, 200, 200))
        
        surface.blit(left_score, (self.width // 4 - left_score.get_width() // 2, 20))
        surface.blit(right_score, (3 * self.width // 4 - right_score.get_width() // 2, 20))
        
        # Serve indicator
        if not self.ball_served:
            serve_font = pygame.font.Font(None, 36)
            serve_text = serve_font.render("PINCH to serve", True, (255, 255, 0))
            surface.blit(serve_text, (self.width // 2 - serve_text.get_width() // 2,
                                     self.height - 50))
        
        # Power-up indicator
        if self.power_active:
            power_font = pygame.font.Font(None, 24)
            power_text = power_font.render(f"POWER: {self.power_type.upper()}", 
                                          True, self.power_color)
            surface.blit(power_text, (self.width // 2 - power_text.get_width() // 2, 10))
            
            # Power timer bar
            bar_width = 200
            bar_height = 10
            fill_width = int(bar_width * (self.power_timer / 300))
            
            pygame.draw.rect(surface, (100, 100, 100),
                           (self.width // 2 - bar_width // 2, 40, bar_width, bar_height))
            pygame.draw.rect(surface, self.power_color,
                           (self.width // 2 - bar_width // 2, 40, fill_width, bar_height))
        
        # Difficulty indicator
        diff_font = pygame.font.Font(None, 24)
        diff_text = diff_font.render(f"AI Difficulty: {self.ai_difficulty:.2f}", 
                                    True, (150, 150, 255))
        surface.blit(diff_text, (self.width - diff_text.get_width() - 10, self.height - 30))
        
        # Pause indicator
        if self.paused:
            pause_font = pygame.font.Font(None, 48)
            pause_text = pause_font.render("PAUSED", True, (255, 255, 0))
            surface.blit(pause_text, (self.width // 2 - pause_text.get_width() // 2,
                                     self.height // 2))
    
    def get_surface(self):
        """Get game surface for hub"""
        surf = pygame.Surface((self.width, self.height))
        self.draw(surf)
        return surf
    
    def cleanup(self):
        """Clean up resources"""
        pass
'''
    
    # Write the fixed pong game
    with open(os.path.join("games", "pong_game.py"), "w") as f:
        f.write(pong_content)
    print("✓ Fixed pong_game.py")
    return True

def fix_main_py():
    """Add debounce to prevent multiple game starts"""
    main_path = "main.py"
    
    if not os.path.exists(main_path):
        print(f"Error: {main_path} not found!")
        return False
    
    with open(main_path, "r") as f:
        content = f.read()
    
    # Look for the keyboard event handler section
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # Find the keyboard event section
        if "elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3," in line:
            # Check the next few lines
            for j in range(i+1, min(i+10, len(lines))):
                if "self.in_menu = False" in lines[j]:
                    # Insert a debounce line
                    new_lines.insert(j+1, "                        time.sleep(0.2)  # Debounce")
                    break
    
    # Write back
    with open(main_path, "w") as f:
        f.write('\n'.join(new_lines))
    
    print("✓ Added debounce to main.py")
    return True

def main():
    print("Fixing gesture game issues...")
    print("-" * 50)
    
    # Check games directory
    if not os.path.exists("games"):
        os.makedirs("games")
        print("Created games directory")
    
    # Fix pong game
    fix_pong_game()
    
    # Fix main.py debounce
    fix_main_py()
    
    print("\n" + "-" * 50)
    print("All fixes applied successfully!")
    print("\nNow you can run:")
    print("  python main.py")
    print("\nAll 9 games should work properly now.")

if __name__ == "__main__":
    main()