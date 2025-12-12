"""
Brick Breaker/Arkanoid Game with power-ups
"""

import pygame
import random
import math
from game_manager import BaseGame

class ArkanoidGame(BaseGame):
    def __init__(self, width=800, height=600):
        super().__init__(width, height)
        self.title = "Brick Breaker"
        pygame.display.set_caption(self.title)
        
        # Colors
        self.bg_color = (15, 20, 35)
        self.paddle_color = (100, 200, 255)
        self.ball_color = (255, 255, 255)
        self.brick_colors = [
            (255, 100, 100),    # Red
            (255, 165, 0),      # Orange
            (255, 255, 100),    # Yellow
            (100, 255, 100),    # Green
            (100, 200, 255),    # Blue
            (200, 100, 255),    # Purple
        ]
        
        # Paddle
        self.paddle_width = 100
        self.paddle_height = 15
        self.paddle_x = width // 2 - self.paddle_width // 2
        self.paddle_y = height - 50
        self.paddle_speed = 8
        
        # Ball
        self.ball_size = 12
        self.reset_ball()
        
        # Bricks
        self.brick_width = 70
        self.brick_height = 25
        self.brick_margin = 5
        self.bricks = []
        
        # Power-ups
        self.power_ups = []
        self.active_powers = {}
        
        # Game state
        self.lives = 3
        self.level = 1
        
        # Generate first level
        self.generate_level()
        
        # Particles
        self.particles = []
    
    def reset_ball(self):
        """Reset ball to paddle"""
        self.ball_x = self.paddle_x + self.paddle_width // 2
        self.ball_y = self.paddle_y - self.ball_size
        self.ball_vx = random.choice([-4, -3, 3, 4])
        self.ball_vy = -5
        self.ball_launched = False
    
    def generate_level(self):
        """Generate bricks for current level"""
        self.bricks = []
        
        rows = min(5 + self.level, 8)
        cols = self.width // (self.brick_width + self.brick_margin)
        
        start_x = (self.width - cols * (self.brick_width + self.brick_margin) + 
                  self.brick_margin) // 2
        
        for row in range(rows):
            brick_hits = min(3, 1 + row // 2)  # More hits for lower rows
            for col in range(cols):
                # Skip some bricks randomly
                if random.random() < 0.1:
                    continue
                
                brick = {
                    'x': start_x + col * (self.brick_width + self.brick_margin),
                    'y': 50 + row * (self.brick_height + self.brick_margin),
                    'width': self.brick_width,
                    'height': self.brick_height,
                    'color': self.brick_colors[row % len(self.brick_colors)],
                    'hits': brick_hits,
                    'max_hits': brick_hits,
                    'has_power': random.random() < 0.2
                }
                self.bricks.append(brick)
    
    def handle_gesture(self, gesture_data):
        """Handle gesture input"""
        direction = gesture_data.get('direction')
        strength = gesture_data.get('strength', 0)
        
        # Move paddle with left/right gestures
        if direction == 'LEFT':
            self.paddle_x -= self.paddle_speed + (strength * 3)
        elif direction == 'RIGHT':
            self.paddle_x += self.paddle_speed + (strength * 3)
        
        # Keep paddle on screen
        self.paddle_x = max(0, min(self.width - self.paddle_width, self.paddle_x))
        
        # Launch ball with pinch
        if not self.ball_launched and gesture_data.get('pinch'):
            self.ball_launched = True
            
            # Add some randomness to launch angle
            angle_variation = random.uniform(-0.2, 0.2)
            speed = math.sqrt(self.ball_vx**2 + self.ball_vy**2)
            angle = math.atan2(self.ball_vy, self.ball_vx) + angle_variation
            
            self.ball_vx = math.cos(angle) * speed
            self.ball_vy = math.sin(angle) * speed
        
        # Activate power with open palm
        if gesture_data.get('open_palm') and 'extra_ball' in self.active_powers:
            self.create_extra_ball()
    
    def create_extra_ball(self):
        """Create an extra ball"""
        # This would create another ball to help clear bricks
        pass
    
    def update(self):
        """Update game state"""
        if self.paused:
            return
        
        # Update ball if launched
        if self.ball_launched:
            self.ball_x += self.ball_vx
            self.ball_y += self.ball_vy
            
            # Wall collisions (left/right)
            if self.ball_x <= 0 or self.ball_x >= self.width - self.ball_size:
                self.ball_vx *= -1
                self.create_wall_particles()
            
            # Ceiling collision
            if self.ball_y <= 0:
                self.ball_vy *= -1
                self.create_wall_particles()
            
            # Floor collision (lose life)
            if self.ball_y >= self.height:
                self.lives -= 1
                self.reset_ball()
                
                if self.lives <= 0:
                    self.game_over = True
                return
            
            # Paddle collision
            if (self.ball_y + self.ball_size >= self.paddle_y and
                self.ball_y <= self.paddle_y + self.paddle_height and
                self.ball_x + self.ball_size >= self.paddle_x and
                self.ball_x <= self.paddle_x + self.paddle_width):
                
                # Calculate bounce angle based on where ball hit paddle
                relative_x = (self.ball_x - self.paddle_x) / self.paddle_width
                angle = (relative_x - 0.5) * math.pi / 3  # -60 to 60 degrees
                
                speed = math.sqrt(self.ball_vx**2 + self.ball_vy**2) * 1.02  # Slight speed increase
                self.ball_vx = math.sin(angle) * speed
                self.ball_vy = -abs(math.cos(angle) * speed)
                
                self.create_paddle_particles()
            
            # Brick collisions
            for brick in self.bricks[:]:
                if (self.ball_x < brick['x'] + brick['width'] and
                    self.ball_x + self.ball_size > brick['x'] and
                    self.ball_y < brick['y'] + brick['height'] and
                    self.ball_y + self.ball_size > brick['y']):
                    
                    # Determine which side was hit
                    overlap_left = (self.ball_x + self.ball_size) - brick['x']
                    overlap_right = (brick['x'] + brick['width']) - self.ball_x
                    overlap_top = (self.ball_y + self.ball_size) - brick['y']
                    overlap_bottom = (brick['y'] + brick['height']) - self.ball_y
                    
                    # Find smallest overlap (that's the side we hit)
                    min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)
                    
                    if min_overlap == overlap_left or min_overlap == overlap_right:
                        self.ball_vx *= -1
                    else:
                        self.ball_vy *= -1
                    
                    # Damage brick
                    brick['hits'] -= 1
                    self.create_brick_particles(brick)
                    
                    if brick['hits'] <= 0:
                        self.score += 10 * brick['max_hits']
                        self.bricks.remove(brick)
                        
                        # Spawn power-up
                        if brick['has_power']:
                            self.spawn_power_up(brick['x'] + brick['width'] // 2,
                                               brick['y'] + brick['height'] // 2)
                    
                    # Only handle one collision per frame
                    break
        
        # Update ball on paddle if not launched
        elif not self.ball_launched:
            self.ball_x = self.paddle_x + self.paddle_width // 2
        
        # Update power-ups
        for power_up in self.power_ups[:]:
            power_up['y'] += 3
            
            # Collect power-up with paddle
            if (power_up['y'] + power_up['size'] >= self.paddle_y and
                power_up['y'] <= self.paddle_y + self.paddle_height and
                power_up['x'] + power_up['size'] >= self.paddle_x and
                power_up['x'] <= self.paddle_x + self.paddle_width):
                
                self.activate_power_up(power_up['type'])
                self.power_ups.remove(power_up)
                self.create_power_particles(power_up['x'], power_up['y'])
            
            # Remove off-screen power-ups
            elif power_up['y'] > self.height:
                self.power_ups.remove(power_up)
        
        # Update active powers
        for power_type in list(self.active_powers.keys()):
            self.active_powers[power_type] -= 1
            if self.active_powers[power_type] <= 0:
                del self.active_powers[power_type]
                
                # Deactivate power
                if power_type == 'big_paddle':
                    self.paddle_width = 100
        
        # Check level completion
        if not self.bricks:
            self.level += 1
            self.generate_level()
            self.reset_ball()
            self.create_level_up_particles()
        
        # Update particles
        self.update_particles()
    
    def spawn_power_up(self, x, y):
        """Spawn a power-up"""
        power_types = ['big_paddle', 'slow_ball', 'extra_ball', 'laser']
        power_type = random.choice(power_types)
        
        colors = {
            'big_paddle': (100, 200, 255),
            'slow_ball': (100, 255, 100),
            'extra_ball': (255, 255, 100),
            'laser': (255, 100, 100)
        }
        
        power_up = {
            'x': x,
            'y': y,
            'size': 20,
            'type': power_type,
            'color': colors[power_type],
            'spin': 0
        }
        
        self.power_ups.append(power_up)
    
    def activate_power_up(self, power_type):
        """Activate a power-up"""
        self.active_powers[power_type] = 600  # 10 seconds at 60 FPS
        
        if power_type == 'big_paddle':
            self.paddle_width = 150
        elif power_type == 'slow_ball':
            speed = math.sqrt(self.ball_vx**2 + self.ball_vy**2)
            self.ball_vx *= 0.7
            self.ball_vy *= 0.7
    
    def create_wall_particles(self):
        """Create particles when ball hits wall"""
        for _ in range(8):
            particle = {
                'x': self.ball_x + self.ball_size // 2,
                'y': self.ball_y + self.ball_size // 2,
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
                'x': self.ball_x + self.ball_size // 2,
                'y': self.ball_y + self.ball_size // 2,
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-3, 3),
                'color': self.paddle_color,
                'life': 25,
                'size': random.randint(2, 4)
            }
            self.particles.append(particle)
    
    def create_brick_particles(self, brick):
        """Create particles when ball hits brick"""
        for _ in range(15):
            particle = {
                'x': brick['x'] + brick['width'] // 2,
                'y': brick['y'] + brick['height'] // 2,
                'vx': random.uniform(-4, 4),
                'vy': random.uniform(-4, 4),
                'color': brick['color'],
                'life': 30,
                'size': random.randint(2, 5)
            }
            self.particles.append(particle)
    
    def create_power_particles(self, x, y):
        """Create particles when collecting power-up"""
        for _ in range(20):
            particle = {
                'x': x,
                'y': y,
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-3, 3),
                'color': (random.randint(100, 255), 
                         random.randint(100, 255), 
                         random.randint(100, 255)),
                'life': 25,
                'size': random.randint(2, 4)
            }
            self.particles.append(particle)
    
    def create_level_up_particles(self):
        """Create particles when leveling up"""
        for _ in range(40):
            particle = {
                'x': self.width // 2,
                'y': self.height // 2,
                'vx': random.uniform(-4, 4),
                'vy': random.uniform(-4, 4),
                'color': (random.randint(100, 255), 
                         random.randint(100, 255), 
                         random.randint(100, 255)),
                'life': 35,
                'size': random.randint(3, 6)
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
        
        # Draw bricks
        for brick in self.bricks:
            # Calculate color based on hits remaining
            hit_ratio = brick['hits'] / brick['max_hits']
            color = (
                int(brick['color'][0] * hit_ratio),
                int(brick['color'][1] * hit_ratio),
                int(brick['color'][2] * hit_ratio)
            )
            
            pygame.draw.rect(target, color,
                           (brick['x'], brick['y'], brick['width'], brick['height']),
                           border_radius=3)
            
            # Draw crack effect if damaged
            if brick['hits'] < brick['max_hits']:
                for _ in range(brick['max_hits'] - brick['hits']):
                    crack_x = brick['x'] + random.randint(5, brick['width'] - 10)
                    crack_y = brick['y'] + random.randint(5, brick['height'] - 10)
                    pygame.draw.line(target, (50, 50, 50),
                                   (crack_x, crack_y),
                                   (crack_x + random.randint(-5, 5),
                                    crack_y + random.randint(-5, 5)), 2)
        
        # Draw paddle with power-up effects
        paddle_color = self.paddle_color
        if 'big_paddle' in self.active_powers:
            paddle_color = (255, 215, 0)  # Gold for big paddle
        
        pygame.draw.rect(target, paddle_color,
                        (self.paddle_x, self.paddle_y,
                         self.paddle_width, self.paddle_height),
                        border_radius=7)
        
        # Draw ball
        ball_color = self.ball_color
        if 'slow_ball' in self.active_powers:
            ball_color = (100, 255, 100)  # Green for slow ball
        
        pygame.draw.circle(target, ball_color,
                          (int(self.ball_x + self.ball_size // 2),
                           int(self.ball_y + self.ball_size // 2)),
                          self.ball_size // 2)
        
        # Draw power-ups
        for power_up in self.power_ups:
            power_up['spin'] += 0.05
            
            # Draw spinning power-up
            angle = power_up['spin']
            points = []
            for i in range(4):
                point_angle = angle + i * math.pi / 2
                px = power_up['x'] + power_up['size'] // 2 + math.cos(point_angle) * power_up['size'] // 2
                py = power_up['y'] + power_up['size'] // 2 + math.sin(point_angle) * power_up['size'] // 2
                points.append((px, py))
            
            pygame.draw.polygon(target, power_up['color'], points)
            
            # Draw letter indicating power type
            font = pygame.font.Font(None, 20)
            letter = power_up['type'][0].upper()
            letter_text = font.render(letter, True, (255, 255, 255))
            target.blit(letter_text, 
                       (power_up['x'] + power_up['size'] // 2 - letter_text.get_width() // 2,
                        power_up['y'] + power_up['size'] // 2 - letter_text.get_height() // 2))
        
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
        font = pygame.font.Font(None, 36)
        
        # Score and level
        score_text = font.render(f"Score: {self.score}", True, (255, 255, 255))
        level_text = font.render(f"Level: {self.level}", True, (255, 255, 255))
        lives_text = font.render(f"Lives: {self.lives}", True, (255, 255, 255))
        
        surface.blit(score_text, (10, 10))
        surface.blit(level_text, (10, 50))
        surface.blit(lives_text, (self.width - lives_text.get_width() - 10, 10))
        
        # Launch instruction
        if not self.ball_launched:
            launch_font = pygame.font.Font(None, 28)
            launch_text = launch_font.render("PINCH to launch ball", True, (255, 255, 0))
            surface.blit(launch_text, (self.width // 2 - launch_text.get_width() // 2,
                                      self.paddle_y - 30))
        
        # Active power-ups
        power_y = 50
        for power_type, timer in self.active_powers.items():
            power_text = font.render(f"{power_type}: {timer//60}s", True, (200, 255, 200))
            surface.blit(power_text, (self.width - power_text.get_width() - 10, power_y))
            power_y += 40
        
        # Game over screen
        if self.game_over:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surface.blit(overlay, (0, 0))
            
            game_over_font = pygame.font.Font(None, 64)
            game_over_text = game_over_font.render("GAME OVER", True, (255, 50, 50))
            final_score = font.render(f"Final Score: {self.score}", True, (255, 255, 255))
            level_reached = font.render(f"Level Reached: {self.level}", True, (255, 255, 255))
            restart_text = font.render("Show UP gesture to restart", True, (100, 255, 100))
            
            surface.blit(game_over_text, (self.width // 2 - game_over_text.get_width() // 2,
                                         self.height // 2 - 80))
            surface.blit(final_score, (self.width // 2 - final_score.get_width() // 2,
                                      self.height // 2 - 20))
            surface.blit(level_reached, (self.width // 2 - level_reached.get_width() // 2,
                                        self.height // 2 + 20))
            surface.blit(restart_text, (self.width // 2 - restart_text.get_width() // 2,
                                       self.height // 2 + 70))
        
        # Level complete screen
        elif not self.bricks and self.ball_launched:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            surface.blit(overlay, (0, 0))
            
            complete_font = pygame.font.Font(None, 72)
            complete_text = complete_font.render(f"LEVEL {self.level} COMPLETE!", 
                                               True, (100, 255, 100))
            
            surface.blit(complete_text, (self.width // 2 - complete_text.get_width() // 2,
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