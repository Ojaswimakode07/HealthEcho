"""
Endless Runner Game with obstacles and power-ups
"""

import pygame
import random
import math
from game_manager import BaseGame

class RunnerGame(BaseGame):
    def __init__(self, width=800, height=600):
        super().__init__(width, height)
        self.title = "Endless Runner"
        pygame.display.set_caption(self.title)
        
        # Colors
        self.sky_color = (135, 206, 235)
        self.ground_color = (34, 139, 34)
        self.player_color = (255, 100, 100)
        self.obstacle_color = (139, 69, 19)
        self.coin_color = (255, 215, 0)
        
        # Player
        self.player_x = 150
        self.player_y = height - 150
        self.player_width = 40
        self.player_height = 60
        self.player_vy = 0
        self.is_jumping = False
        self.is_sliding = False
        self.lane = 1  # 0: left, 1: center, 2: right
        
        # Game world
        self.ground_y = height - 100
        self.scroll_speed = 5
        self.base_speed = 5
        self.boost_multiplier = 1.5
        
        # Obstacles and coins
        self.obstacles = []
        self.coins = []
        self.power_ups = []
        
        # Spawn timers
        self.obstacle_timer = 0
        self.coin_timer = 0
        
        # Game state
        self.distance = 0
        self.lives = 3
        self.invincible = 0
        
        # Particles
        self.particles = []
        
        # Lane positions
        self.lane_positions = [width // 4 - 50, width // 2 - 25, 3 * width // 4]
    
    def handle_gesture(self, gesture_data):
        """Handle gesture input"""
        direction = gesture_data.get('direction')
        strength = gesture_data.get('strength', 0)
        
        # Jump
        if direction == 'UP' and not self.is_jumping:
            self.player_vy = -15 - (strength * 5)
            self.is_jumping = True
            self.is_sliding = False
        
        # Slide
        elif direction == 'DOWN' and not self.is_sliding:
            self.is_sliding = True
            self.player_height = 30
            self.player_y = self.ground_y - self.player_height
        
        # Change lanes
        elif direction == 'LEFT':
            self.lane = max(0, self.lane - 1)
        elif direction == 'RIGHT':
            self.lane = min(2, self.lane + 1)
        
        # Speed boost with pinch
        self.scroll_speed = self.base_speed
        if gesture_data.get('pinch'):
            self.scroll_speed = int(self.base_speed * self.boost_multiplier)
        
        # Stop sliding when gesture ends
        if direction is None and self.is_sliding:
            self.is_sliding = False
            self.player_height = 60
            self.player_y = self.ground_y - self.player_height
    
    def update(self):
        """Update game state"""
        if self.paused:
            return
        
        # Update player physics
        self.player_vy += 0.8  # Gravity
        self.player_y += self.player_vy
        
        # Ground collision
        if self.player_y > self.ground_y - self.player_height:
            self.player_y = self.ground_y - self.player_height
            self.player_vy = 0
            self.is_jumping = False
        
        # Update player x based on lane
        target_x = self.lane_positions[self.lane]
        self.player_x += (target_x - self.player_x) * 0.2
        
        # Update distance
        self.distance += self.scroll_speed / 10
        
        # Spawn obstacles
        self.obstacle_timer -= 1
        if self.obstacle_timer <= 0:
            self.spawn_obstacle()
            self.obstacle_timer = random.randint(30, 90)
        
        # Spawn coins
        self.coin_timer -= 1
        if self.coin_timer <= 0:
            self.spawn_coin()
            self.coin_timer = random.randint(15, 45)
        
        # Update obstacles
        for obstacle in self.obstacles[:]:
            obstacle['x'] -= self.scroll_speed
            
            # Check collision
            if (self.player_x < obstacle['x'] + obstacle['width'] and
                self.player_x + self.player_width > obstacle['x'] and
                self.player_y < obstacle['y'] + obstacle['height'] and
                self.player_y + self.player_height > obstacle['y']):
                
                if self.invincible <= 0:
                    self.lives -= 1
                    self.invincible = 60  # 1 second invincibility
                    self.create_hit_particles()
                
                if self.lives <= 0:
                    self.game_over = True
            
            # Remove off-screen obstacles
            if obstacle['x'] < -obstacle['width']:
                self.obstacles.remove(obstacle)
        
        # Update coins
        for coin in self.coins[:]:
            coin['x'] -= self.scroll_speed
            
            # Check collection
            if (self.player_x < coin['x'] + coin['size'] and
                self.player_x + self.player_width > coin['x'] and
                self.player_y < coin['y'] + coin['size'] and
                self.player_y + self.player_height > coin['y']):
                
                self.score += 10
                self.create_coin_particles(coin['x'], coin['y'])
                self.coins.remove(coin)
            
            # Remove off-screen coins
            if coin['x'] < -coin['size']:
                self.coins.remove(coin)
        
        # Update invincibility
        if self.invincible > 0:
            self.invincible -= 1
        
        # Update particles
        self.update_particles()
        
        # Increase difficulty over time
        self.base_speed = 5 + (self.distance / 1000)
    
    def spawn_obstacle(self):
        """Spawn a new obstacle"""
        types = [
            {'width': 40, 'height': 40, 'y': self.ground_y - 40},  # Low
            {'width': 30, 'height': 60, 'y': self.ground_y - 60},  # Medium
            {'width': 50, 'height': 30, 'y': self.ground_y - 30}   # Wide
        ]
        
        obstacle_type = random.choice(types)
        lane = random.randint(0, 2)
        
        obstacle = {
            'x': self.width,
            'y': obstacle_type['y'],
            'width': obstacle_type['width'],
            'height': obstacle_type['height'],
            'lane': lane,
            'color': self.obstacle_color
        }
        
        self.obstacles.append(obstacle)
    
    def spawn_coin(self):
        """Spawn a new coin"""
        lane = random.randint(0, 2)
        height_variation = random.randint(-50, 50)
        
        coin = {
            'x': self.width,
            'y': self.ground_y - 100 + height_variation,
            'size': 20,
            'lane': lane,
            'color': self.coin_color,
            'spin': 0
        }
        
        self.coins.append(coin)
    
    def create_hit_particles(self):
        """Create particles when player hits obstacle"""
        for _ in range(20):
            particle = {
                'x': self.player_x + self.player_width // 2,
                'y': self.player_y + self.player_height // 2,
                'vx': random.uniform(-5, 5),
                'vy': random.uniform(-5, 5),
                'color': (255, 50, 50),
                'life': 30,
                'size': random.randint(2, 5)
            }
            self.particles.append(particle)
    
    def create_coin_particles(self, x, y):
        """Create particles when collecting coin"""
        for _ in range(15):
            particle = {
                'x': x,
                'y': y,
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-3, 3),
                'color': self.coin_color,
                'life': 25,
                'size': random.randint(1, 3)
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
        
        # Draw sky
        target.fill(self.sky_color)
        
        # Draw clouds (background)
        for i in range(5):
            cloud_x = (self.distance * 0.5 + i * 200) % (self.width + 200) - 100
            cloud_y = 50 + i * 40
            cloud_size = 40 + i * 10
            
            pygame.draw.circle(target, (255, 255, 255), 
                             (int(cloud_x), cloud_y), cloud_size)
            pygame.draw.circle(target, (255, 255, 255), 
                             (int(cloud_x + cloud_size * 0.7), cloud_y), cloud_size * 0.8)
            pygame.draw.circle(target, (255, 255, 255), 
                             (int(cloud_x - cloud_size * 0.7), cloud_y), cloud_size * 0.8)
        
        # Draw ground
        pygame.draw.rect(target, self.ground_color,
                        (0, self.ground_y, self.width, self.height - self.ground_y))
        
        # Draw lane markers
        for lane_pos in self.lane_positions:
            for y in range(0, self.height - self.ground_y, 30):
                offset = (self.distance * 2) % 60
                if (y + offset) % 60 < 30:
                    pygame.draw.rect(target, (255, 255, 255),
                                   (lane_pos - 2, self.ground_y + y, 4, 20))
        
        # Draw obstacles
        for obstacle in self.obstacles:
            pygame.draw.rect(target, obstacle['color'],
                           (obstacle['x'], obstacle['y'],
                            obstacle['width'], obstacle['height']),
                           border_radius=5)
        
        # Draw coins
        for coin in self.coins:
            coin['spin'] += 0.1
            pygame.draw.circle(target, coin['color'],
                             (int(coin['x'] + coin['size'] // 2),
                              int(coin['y'] + coin['size'] // 2)),
                             coin['size'] // 2)
            
            # Draw shine effect
            shine_x = coin['x'] + coin['size'] // 2 + math.cos(coin['spin']) * 3
            shine_y = coin['y'] + coin['size'] // 2 + math.sin(coin['spin']) * 3
            pygame.draw.circle(target, (255, 255, 255), 
                             (int(shine_x), int(shine_y)), 3)
        
        # Draw player with animation
        player_color = self.player_color
        if self.invincible > 0 and self.invincible % 10 < 5:
            player_color = (255, 255, 255)  # Blink when invincible
        
        # Player body
        pygame.draw.rect(target, player_color,
                        (self.player_x, self.player_y,
                         self.player_width, self.player_height),
                        border_radius=10)
        
        # Player head
        head_radius = 15
        head_y = self.player_y - head_radius
        pygame.draw.circle(target, player_color,
                          (int(self.player_x + self.player_width // 2), head_y),
                          head_radius)
        
        # Player eyes
        eye_offset = 5 if self.scroll_speed > self.base_speed else 3  # Squint when boosting
        pygame.draw.circle(target, (0, 0, 0),
                          (int(self.player_x + self.player_width // 2 - eye_offset), head_y - 3), 3)
        pygame.draw.circle(target, (0, 0, 0),
                          (int(self.player_x + self.player_width // 2 + eye_offset), head_y - 3), 3)
        
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
        # Score and distance
        font = pygame.font.Font(None, 36)
        score_text = font.render(f"Score: {self.score}", True, (255, 255, 255))
        distance_text = font.render(f"Distance: {self.distance:.0f}m", True, (255, 255, 255))
        
        surface.blit(score_text, (10, 10))
        surface.blit(distance_text, (10, 50))
        
        # Lives
        for i in range(self.lives):
            heart_x = self.width - 40 - i * 30
            heart_y = 20
            self.draw_heart(surface, heart_x, heart_y, 15, (255, 100, 100))
        
        # Speed indicator
        if self.scroll_speed > self.base_speed:
            speed_text = font.render("SPEED BOOST!", True, (255, 255, 0))
            surface.blit(speed_text, (self.width // 2 - speed_text.get_width() // 2, 10))
        
        # Game over screen
        if self.game_over:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surface.blit(overlay, (0, 0))
            
            game_over_font = pygame.font.Font(None, 64)
            game_over_text = game_over_font.render("GAME OVER", True, (255, 50, 50))
            final_score = font.render(f"Final Score: {self.score}", True, (255, 255, 255))
            final_distance = font.render(f"Distance: {self.distance:.0f}m", True, (255, 255, 255))
            restart_text = font.render("Show UP gesture to restart", True, (100, 255, 100))
            
            surface.blit(game_over_text, (self.width // 2 - game_over_text.get_width() // 2,
                                         self.height // 2 - 80))
            surface.blit(final_score, (self.width // 2 - final_score.get_width() // 2,
                                      self.height // 2 - 20))
            surface.blit(final_distance, (self.width // 2 - final_distance.get_width() // 2,
                                         self.height // 2 + 20))
            surface.blit(restart_text, (self.width // 2 - restart_text.get_width() // 2,
                                       self.height // 2 + 70))
        
        # Pause indicator
        if self.paused:
            pause_font = pygame.font.Font(None, 48)
            pause_text = pause_font.render("PAUSED", True, (255, 255, 0))
            surface.blit(pause_text, (self.width // 2 - pause_text.get_width() // 2,
                                     self.height // 2))
    
    def draw_heart(self, surface, x, y, size, color):
        """Draw a heart shape"""
        points = []
        for angle in range(0, 360, 10):
            rad = math.radians(angle)
            heart_x = 16 * (math.sin(rad) ** 3)
            heart_y = -(13 * math.cos(rad) - 5 * math.cos(2 * rad) - 
                       2 * math.cos(3 * rad) - math.cos(4 * rad))
            
            points.append((x + heart_x * size / 16, y + heart_y * size / 16))
        
        if len(points) > 2:
            pygame.draw.polygon(surface, color, points)
    
    def get_surface(self):
        """Get game surface for hub"""
        surf = pygame.Surface((self.width, self.height))
        self.draw(surf)
        return surf
    
    def cleanup(self):
        """Clean up resources"""
        pass