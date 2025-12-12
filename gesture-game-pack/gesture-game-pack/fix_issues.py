"""
Quick fix script for gesture game hub issues
"""

import os
import sys

def create_flappy_game():
    """Create missing flappy_game.py file"""
    flappy_content = '''"""
Flappy Bird Style Game with gesture control
"""

import pygame
import random
import math
from game_manager import BaseGame

class FlappyGame(BaseGame):
    def __init__(self, width=800, height=600):
        super().__init__(width, height)
        self.title = "Flappy Flyer"
        pygame.display.set_caption(self.title)
        
        # Colors
        self.sky_color = (135, 206, 235)
        self.ground_color = (222, 184, 135)
        self.bird_color = (255, 100, 100)
        self.pipe_color = (100, 180, 100)
        self.cloud_color = (255, 255, 255)
        
        # Bird
        self.bird_x = 200
        self.bird_y = height // 2
        self.bird_radius = 20
        self.bird_vy = 0
        self.bird_flap = 0
        
        # Physics
        self.gravity = 0.5
        self.flap_strength = -8
        self.max_fall_speed = 10
        
        # Pipes
        self.pipes = []
        self.pipe_width = 80
        self.pipe_gap = 200
        self.pipe_speed = 3
        self.pipe_spawn_timer = 0
        
        # Game state
        self.passed_pipes = 0
        self.high_score = 0
        
        # Background elements
        self.clouds = []
        for _ in range(5):
            self.clouds.append({
                'x': random.randint(0, width),
                'y': random.randint(50, 200),
                'speed': random.uniform(0.2, 0.5),
                'size': random.randint(30, 60)
            })
        
        # Particles
        self.particles = []
    
    def handle_gesture(self, gesture_data):
        """Handle gesture input"""
        direction = gesture_data.get('direction')
        strength = gesture_data.get('strength', 0)
        
        # Flap with UP gesture
        if direction == 'UP':
            self.bird_vy = self.flap_strength - (strength * 3)
            self.bird_flap = 10  # Flap animation
            self.create_flap_particles()
        
        # Power dive with DOWN gesture
        elif direction == 'DOWN' and self.bird_vy > 0:
            self.bird_vy += 3  # Faster dive
        
        # Boost with pinch
        if gesture_data.get('pinch'):
            self.pipe_speed = 5
        else:
            self.pipe_speed = 3
        
        # Pause with open palm
        if gesture_data.get('open_palm'):
            self.paused = not self.paused
    
    def update(self):
        """Update game state"""
        if self.paused or self.game_over:
            return
        
        # Update bird physics
        self.bird_vy += self.gravity
        self.bird_vy = min(self.bird_vy, self.max_fall_speed)
        self.bird_y += self.bird_vy
        
        # Update flap animation
        if self.bird_flap > 0:
            self.bird_flap -= 1
        
        # Check boundaries
        if self.bird_y < self.bird_radius:
            self.bird_y = self.bird_radius
            self.bird_vy = 0
        
        if self.bird_y > self.height - 100 - self.bird_radius:
            self.game_over = True
            return
        
        # Spawn pipes
        self.pipe_spawn_timer -= 1
        if self.pipe_spawn_timer <= 0:
            self.spawn_pipe()
            self.pipe_spawn_timer = random.randint(90, 150)
        
        # Update pipes
        for pipe in self.pipes[:]:
            pipe['x'] -= self.pipe_speed
            
            # Check collision
            if (self.bird_x + self.bird_radius > pipe['x'] and
                self.bird_x - self.bird_radius < pipe['x'] + self.pipe_width):
                
                if (self.bird_y - self.bird_radius < pipe['top_height'] or
                    self.bird_y + self.bird_radius > pipe['top_height'] + self.pipe_gap):
                    
                    self.game_over = True
                    self.create_crash_particles()
                    return
            
            # Check if pipe passed
            if pipe['x'] + self.pipe_width < self.bird_x and not pipe.get('passed'):
                pipe['passed'] = True
                self.passed_pipes += 1
                self.score += 10
                self.create_score_particles()
            
            # Remove off-screen pipes
            if pipe['x'] < -self.pipe_width:
                self.pipes.remove(pipe)
        
        # Update clouds
        for cloud in self.clouds:
            cloud['x'] -= cloud['speed']
            if cloud['x'] < -cloud['size'] * 2:
                cloud['x'] = self.width + cloud['size'] * 2
                cloud['y'] = random.randint(50, 200)
        
        # Update particles
        self.update_particles()
        
        # Update high score
        if self.score > self.high_score:
            self.high_score = self.score
    
    def spawn_pipe(self):
        """Spawn a new pipe"""
        min_height = 100
        max_height = self.height - 200 - self.pipe_gap
        top_height = random.randint(min_height, max_height)
        
        pipe = {
            'x': self.width,
            'top_height': top_height,
            'color': self.pipe_color,
            'passed': False
        }
        
        self.pipes.append(pipe)
    
    def create_flap_particles(self):
        """Create particles when bird flaps"""
        for _ in range(8):
            angle = random.uniform(math.pi - 0.5, math.pi + 0.5)
            speed = random.uniform(1, 3)
            
            particle = {
                'x': self.bird_x - self.bird_radius,
                'y': self.bird_y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'color': self.bird_color,
                'life': 20,
                'size': random.randint(2, 4)
            }
            self.particles.append(particle)
    
    def create_crash_particles(self):
        """Create particles when bird crashes"""
        for _ in range(30):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 6)
            
            particle = {
                'x': self.bird_x,
                'y': self.bird_y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'color': self.bird_color,
                'life': 40,
                'size': random.randint(3, 6)
            }
            self.particles.append(particle)
    
    def create_score_particles(self):
        """Create particles when scoring"""
        for _ in range(15):
            particle = {
                'x': self.width // 2,
                'y': 100,
                'vx': random.uniform(-2, 2),
                'vy': random.uniform(-2, 2),
                'color': (255, 215, 0),
                'life': 30,
                'size': random.randint(2, 4)
            }
            self.particles.append(particle)
    
    def update_particles(self):
        """Update particle effects"""
        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['vy'] += 0.1  # Gravity for particles
            particle['life'] -= 1
            
            if particle['life'] <= 0:
                self.particles.remove(particle)
    
    def draw(self, surface=None):
        """Draw game"""
        target = surface or self.screen
        
        # Draw sky
        target.fill(self.sky_color)
        
        # Draw clouds
        for cloud in self.clouds:
            # Cloud with multiple circles
            pygame.draw.circle(target, self.cloud_color, 
                             (int(cloud['x']), cloud['y']), cloud['size'])
            pygame.draw.circle(target, self.cloud_color, 
                             (int(cloud['x'] + cloud['size'] * 0.7), cloud['y']), cloud['size'] * 0.8)
            pygame.draw.circle(target, self.cloud_color, 
                             (int(cloud['x'] - cloud['size'] * 0.7), cloud['y']), cloud['size'] * 0.8)
            pygame.draw.circle(target, self.cloud_color, 
                             (int(cloud['x']), cloud['y'] - cloud['size'] * 0.5), cloud['size'] * 0.7)
        
        # Draw pipes
        for pipe in self.pipes:
            # Top pipe
            pygame.draw.rect(target, pipe['color'],
                           (pipe['x'], 0, self.pipe_width, pipe['top_height']))
            
            # Pipe cap
            pygame.draw.rect(target, (80, 140, 80),
                           (pipe['x'] - 5, pipe['top_height'] - 20,
                            self.pipe_width + 10, 20),
                           border_radius=5)
            
            # Bottom pipe
            bottom_y = pipe['top_height'] + self.pipe_gap
            bottom_height = self.height - 100 - bottom_y
            
            pygame.draw.rect(target, pipe['color'],
                           (pipe['x'], bottom_y, self.pipe_width, bottom_height))
            
            # Pipe cap
            pygame.draw.rect(target, (80, 140, 80),
                           (pipe['x'] - 5, bottom_y,
                            self.pipe_width + 10, 20),
                           border_radius=5)
        
        # Draw bird with animation
        bird_color = self.bird_color
        
        # Flap animation
        wing_offset = 0
        if self.bird_flap > 0:
            wing_offset = 10
        
        # Bird body
        pygame.draw.circle(target, bird_color,
                          (int(self.bird_x), int(self.bird_y)),
                          self.bird_radius)
        
        # Bird wing (animated)
        wing_points = [
            (self.bird_x - 15, self.bird_y),
            (self.bird_x - 25, self.bird_y - 10 + wing_offset),
            (self.bird_x - 15, self.bird_y - 5)
        ]
        pygame.draw.polygon(target, (200, 80, 80), wing_points)
        
        # Bird eye
        pygame.draw.circle(target, (0, 0, 0),
                          (int(self.bird_x + 8), int(self.bird_y - 5)), 4)
        pygame.draw.circle(target, (255, 255, 255),
                          (int(self.bird_x + 10), int(self.bird_y - 6)), 1)
        
        # Bird beak
        beak_points = [
            (self.bird_x + 15, self.bird_y - 3),
            (self.bird_x + 25, self.bird_y),
            (self.bird_x + 15, self.bird_y + 3)
        ]
        pygame.draw.polygon(target, (255, 165, 0), beak_points)
        
        # Draw ground
        pygame.draw.rect(target, self.ground_color,
                        (0, self.height - 100, self.width, 100))
        
        # Draw grass on ground
        for x in range(0, self.width, 20):
            height = random.randint(5, 15)
            pygame.draw.line(target, (100, 180, 100),
                           (x, self.height - 100),
                           (x, self.height - 100 - height), 2)
        
        # Draw particles
        for particle in self.particles:
            alpha = int(255 * (particle['life'] / 30))
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
        font = pygame.font.Font(None, 48)
        small_font = pygame.font.Font(None, 24)
        
        # Score
        score_text = font.render(str(self.score), True, (255, 255, 255))
        surface.blit(score_text, (self.width // 2 - score_text.get_width() // 2, 50))
        
        # High score
        high_score_text = small_font.render(f"High Score: {self.high_score}", 
                                           True, (200, 200, 200))
        surface.blit(high_score_text, (self.width - high_score_text.get_width() - 10, 10))
        
        # Speed indicator
        if self.pipe_speed > 3:
            speed_text = small_font.render("SPEED BOOST!", True, (255, 255, 0))
            surface.blit(speed_text, (10, 10))
        
        # Game over screen
        if self.game_over:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surface.blit(overlay, (0, 0))
            
            game_over_font = pygame.font.Font(None, 64)
            game_over_text = game_over_font.render("GAME OVER", True, (255, 50, 50))
            final_score = font.render(f"Score: {self.score}", True, (255, 255, 255))
            high_score = font.render(f"High Score: {self.high_score}", True, (255, 255, 255))
            restart_text = font.render("Show UP gesture to restart", True, (100, 255, 100))
            
            surface.blit(game_over_text, (self.width // 2 - game_over_text.get_width() // 2,
                                         self.height // 2 - 80))
            surface.blit(final_score, (self.width // 2 - final_score.get_width() // 2,
                                      self.height // 2 - 20))
            surface.blit(high_score, (self.width // 2 - high_score.get_width() // 2,
                                     self.height // 2 + 20))
            surface.blit(restart_text, (self.width // 2 - restart_text.get_width() // 2,
                                       self.height // 2 + 70))
        
        # Start screen
        elif self.score == 0 and len(self.pipes) == 0:
            start_font = pygame.font.Font(None, 36)
            start_text = start_font.render("Show UP gesture to flap", True, (255, 255, 0))
            surface.blit(start_text, (self.width // 2 - start_text.get_width() // 2,
                                     self.height // 2))
        
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
    
    flappy_path = os.path.join("games", "flappy_game.py")
    with open(flappy_path, "w") as f:
        f.write(flappy_content)
    print(f"Created {flappy_path}")

def fix_pong_game():
    """Fix the serve_delay attribute in pong_game.py"""
    pong_path = os.path.join("games", "pong_game.py")
    
    if not os.path.exists(pong_path):
        print(f"Error: {pong_path} not found!")
        return False
    
    with open(pong_path, "r") as f:
        content = f.read()
    
    # Check if serve_delay is defined
    if "self.serve_delay = " not in content:
        # Find the reset_ball method and add the attribute
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            # Look for the __init__ method to add serve_delay
            if "__init__" in line and "def" in line and "self" in line:
                # Find the end of __init__ method
                j = i + 1
                while j < len(lines) and (lines[j].startswith(' ') or lines[j].startswith('\t')):
                    j += 1
                # Insert serve_delay after game state comment
                for k in range(i, j):
                    if "# Game state" in lines[k]:
                        new_lines.insert(k + 1, "        self.serve_delay = 60  # Serve delay in frames")
                        break
        
        content = '\n'.join(new_lines)
    
    # Write the fixed content back
    with open(pong_path, "w") as f:
        f.write(content)
    
    print(f"Fixed {pong_path}")
    return True

def main():
    """Main fix function"""
    print("Fixing gesture game hub issues...")
    print("-" * 40)
    
    # Check if games directory exists
    if not os.path.exists("games"):
        os.makedirs("games")
        print("Created games directory")
    
    # Create flappy_game.py if missing
    flappy_path = os.path.join("games", "flappy_game.py")
    if not os.path.exists(flappy_path):
        print("Creating missing flappy_game.py...")
        create_flappy_game()
    else:
        print("flappy_game.py already exists")
    
    # Fix pong_game.py
    print("\nFixing pong_game.py...")
    if fix_pong_game():
        print("✓ pong_game.py fixed successfully")
    else:
        print("✗ Could not fix pong_game.py")
    
    print("\n" + "-" * 40)
    print("Fix complete! Try running 'python main.py' again.")
    print("\nIf you still have issues, try:")
    print("1. Delete the games/ folder")
    print("2. Run this fix script again")
    print("3. Run 'python main.py'")

if __name__ == "__main__":
    main()