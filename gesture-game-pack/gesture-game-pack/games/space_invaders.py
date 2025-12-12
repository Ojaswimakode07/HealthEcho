"""
Space Invaders Style Game
"""

import pygame
import random
import math
from game_manager import BaseGame

class SpaceInvaders(BaseGame):
    def __init__(self, width=800, height=600):
        super().__init__(width, height)
        self.title = "Space Invaders"
        pygame.display.set_caption(self.title)
        
        # Colors
        self.space_color = (10, 10, 30)
        self.star_color = (255, 255, 255)
        self.player_color = (100, 200, 255)
        self.bullet_color = (255, 255, 100)
        self.enemy_colors = [
            (255, 100, 100),    # Red
            (255, 165, 100),    # Orange
            (255, 255, 100),    # Yellow
            (100, 255, 100),    # Green
        ]
        self.power_color = (255, 215, 0)
        
        # Player
        self.player_x = width // 2
        self.player_y = height - 50
        self.player_width = 50
        self.player_height = 30
        self.player_speed = 6
        
        # Bullets
        self.bullets = []
        self.bullet_speed = 8
        self.shoot_cooldown = 0
        
        # Enemies
        self.enemies = []
        self.enemy_speed = 1
        self.enemy_direction = 1
        self.enemy_move_timer = 0
        self.enemy_shoot_chance = 0.005
        
        # Power-ups
        self.power_ups = []
        self.active_powers = {}
        
        # Stars background
        self.stars = []
        for _ in range(100):
            self.stars.append({
                'x': random.randint(0, width),
                'y': random.randint(0, height),
                'size': random.uniform(0.5, 2),
                'speed': random.uniform(0.1, 0.5),
                'twinkle': random.uniform(0, math.pi * 2)
            })
        
        # Game state
        self.lives = 3
        self.wave = 1
        
        # Particles
        self.particles = []
        
        # Generate first wave
        self.generate_wave()
    
    def generate_wave(self):
        """Generate a wave of enemies"""
        self.enemies = []
        
        rows = min(3 + self.wave // 2, 6)
        cols = min(6 + self.wave, 12)
        
        start_x = 100
        start_y = 50
        
        for row in range(rows):
            for col in range(cols):
                enemy_type = min(row, 3)  # Different types based on row
                
                enemy = {
                    'x': start_x + col * 60,
                    'y': start_y + row * 50,
                    'width': 40,
                    'height': 30,
                    'type': enemy_type,
                    'color': self.enemy_colors[enemy_type],
                    'points': (enemy_type + 1) * 10,
                    'shoot_chance': 0.001 * (enemy_type + 1)
                }
                self.enemies.append(enemy)
    
    def handle_gesture(self, gesture_data):
        """Handle gesture input"""
        direction = gesture_data.get('direction')
        
        # Move player with left/right gestures
        if direction == 'LEFT':
            self.player_x -= self.player_speed
        elif direction == 'RIGHT':
            self.player_x += self.player_speed
        
        # Keep player on screen
        self.player_x = max(self.player_width // 2, 
                           min(self.width - self.player_width // 2, self.player_x))
        
        # Shoot with UP gesture
        if direction == 'UP' and self.shoot_cooldown <= 0:
            self.shoot_bullet()
            self.shoot_cooldown = 15
        
        # Activate shield with open palm
        if gesture_data.get('open_palm') and 'shield' not in self.active_powers:
            self.active_powers['shield'] = 300  # 5 seconds
        
        # Rapid fire with pinch
        if gesture_data.get('pinch'):
            self.bullet_speed = 12
            self.shoot_cooldown = max(5, self.shoot_cooldown)
        else:
            self.bullet_speed = 8
    
    def shoot_bullet(self):
        """Shoot a bullet from player"""
        bullet = {
            'x': self.player_x,
            'y': self.player_y - self.player_height // 2,
            'width': 4,
            'height': 15,
            'speed': self.bullet_speed,
            'type': 'player'
        }
        self.bullets.append(bullet)
        self.create_shoot_particles()
    
    def shoot_enemy_bullet(self, enemy):
        """Enemy shoots a bullet"""
        bullet = {
            'x': enemy['x'],
            'y': enemy['y'] + enemy['height'],
            'width': 4,
            'height': 15,
            'speed': 4,
            'type': 'enemy',
            'color': (255, 100, 100)
        }
        self.bullets.append(bullet)
    
    def update(self):
        """Update game state"""
        if self.paused:
            return
        
        # Update cooldown
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        
        # Update stars
        for star in self.stars:
            star['y'] += star['speed']
            star['twinkle'] += 0.05
            
            if star['y'] > self.height:
                star['y'] = 0
                star['x'] = random.randint(0, self.width)
        
        # Update bullets
        for bullet in self.bullets[:]:
            if bullet['type'] == 'player':
                bullet['y'] -= bullet['speed']
            else:
                bullet['y'] += bullet['speed']
            
            # Remove off-screen bullets
            if (bullet['y'] < 0 or bullet['y'] > self.height or
                bullet['x'] < 0 or bullet['x'] > self.width):
                self.bullets.remove(bullet)
                continue
            
            # Player bullet collision with enemies
            if bullet['type'] == 'player':
                for enemy in self.enemies[:]:
                    if (bullet['x'] > enemy['x'] - enemy['width'] // 2 and
                        bullet['x'] < enemy['x'] + enemy['width'] // 2 and
                        bullet['y'] > enemy['y'] - enemy['height'] // 2 and
                        bullet['y'] < enemy['y'] + enemy['height'] // 2):
                        
                        self.score += enemy['points']
                        self.create_explosion(enemy['x'], enemy['y'], enemy['color'])
                        self.enemies.remove(enemy)
                        
                        if bullet in self.bullets:
                            self.bullets.remove(bullet)
                        
                        # Chance to spawn power-up
                        if random.random() < 0.1:
                            self.spawn_power_up(enemy['x'], enemy['y'])
                        
                        break
            
            # Enemy bullet collision with player
            elif bullet['type'] == 'enemy':
                if ('shield' not in self.active_powers and
                    bullet['x'] > self.player_x - self.player_width // 2 and
                    bullet['x'] < self.player_x + self.player_width // 2 and
                    bullet['y'] > self.player_y - self.player_height // 2 and
                    bullet['y'] < self.player_y + self.player_height // 2):
                    
                    self.lives -= 1
                    self.create_hit_particles()
                    
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    
                    if self.lives <= 0:
                        self.game_over = True
                        return
        
        # Update enemies
        self.enemy_move_timer -= 1
        
        if self.enemy_move_timer <= 0:
            # Move all enemies
            move_down = False
            
            for enemy in self.enemies:
                enemy['x'] += self.enemy_speed * self.enemy_direction
                
                # Check if enemy hits edge
                if (enemy['x'] > self.width - 50 or enemy['x'] < 50):
                    move_down = True
            
            # Change direction and move down if needed
            if move_down:
                self.enemy_direction *= -1
                for enemy in self.enemies:
                    enemy['y'] += 20
                    enemy['x'] += self.enemy_speed * self.enemy_direction * 2
            
            self.enemy_move_timer = 30 - min(self.wave * 2, 25)
            
            # Enemies shoot
            for enemy in self.enemies:
                if random.random() < enemy['shoot_chance']:
                    self.shoot_enemy_bullet(enemy)
        
        # Update power-ups
        for power_up in self.power_ups[:]:
            power_up['y'] += 2
            power_up['spin'] += 0.05
            
            # Collect power-up
            if (power_up['y'] > self.player_y - self.player_height // 2 and
                power_up['y'] < self.player_y + self.player_height // 2 and
                power_up['x'] > self.player_x - self.player_width // 2 and
                power_up['x'] < self.player_x + self.player_width // 2):
                
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
        
        # Check if enemies reached bottom
        for enemy in self.enemies:
            if enemy['y'] > self.height - 100:
                self.game_over = True
                return
        
        # Check wave completion
        if not self.enemies:
            self.wave += 1
            self.enemy_speed = min(3, 1 + self.wave * 0.1)
            self.generate_wave()
            self.create_wave_particles()
        
        # Update particles
        self.update_particles()
    
    def spawn_power_up(self, x, y):
        """Spawn a power-up"""
        power_types = ['rapid_fire', 'shield', 'double_shot', 'extra_life']
        power_type = random.choice(power_types)
        
        power_up = {
            'x': x,
            'y': y,
            'size': 20,
            'type': power_type,
            'color': self.power_color,
            'spin': 0
        }
        
        self.power_ups.append(power_up)
    
    def activate_power_up(self, power_type):
        """Activate a power-up"""
        if power_type == 'rapid_fire':
            self.active_powers['rapid_fire'] = 600
            self.shoot_cooldown = 5
        elif power_type == 'shield':
            self.active_powers['shield'] = 600
        elif power_type == 'double_shot':
            self.active_powers['double_shot'] = 300
        elif power_type == 'extra_life':
            self.lives = min(5, self.lives + 1)
    
    def create_shoot_particles(self):
        """Create particles when shooting"""
        for _ in range(5):
            particle = {
                'x': self.player_x,
                'y': self.player_y - self.player_height // 2,
                'vx': random.uniform(-1, 1),
                'vy': random.uniform(-3, -1),
                'color': self.bullet_color,
                'life': 15,
                'size': random.randint(1, 3)
            }
            self.particles.append(particle)
    
    def create_explosion(self, x, y, color):
        """Create explosion particles"""
        for _ in range(20):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 4)
            
            particle = {
                'x': x,
                'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'color': color,
                'life': 30,
                'size': random.randint(2, 5)
            }
            self.particles.append(particle)
    
    def create_hit_particles(self):
        """Create particles when player is hit"""
        for _ in range(30):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 5)
            
            particle = {
                'x': self.player_x,
                'y': self.player_y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'color': self.player_color,
                'life': 25,
                'size': random.randint(2, 4)
            }
            self.particles.append(particle)
    
    def create_power_particles(self, x, y):
        """Create particles when collecting power-up"""
        for _ in range(15):
            particle = {
                'x': x,
                'y': y,
                'vx': random.uniform(-2, 2),
                'vy': random.uniform(-2, 2),
                'color': self.power_color,
                'life': 20,
                'size': random.randint(1, 3)
            }
            self.particles.append(particle)
    
    def create_wave_particles(self):
        """Create particles when completing a wave"""
        for _ in range(40):
            particle = {
                'x': self.width // 2,
                'y': self.height // 2,
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-3, 3),
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
        target.fill(self.space_color)
        
        # Draw stars
        for star in self.stars:
            brightness = 0.5 + 0.5 * math.sin(star['twinkle'])
            color = (
                int(self.star_color[0] * brightness),
                int(self.star_color[1] * brightness),
                int(self.star_color[2] * brightness)
            )
            pygame.draw.circle(target, color,
                             (int(star['x']), int(star['y'])),
                             star['size'])
        
        # Draw enemies
        for enemy in self.enemies:
            # Enemy body
            points = []
            for i in range(8):
                angle = i * math.pi / 4
                radius = enemy['width'] // 2
                if i % 2 == 0:
                    radius = enemy['width'] // 3
                
                px = enemy['x'] + math.cos(angle) * radius
                py = enemy['y'] + math.sin(angle) * radius
                points.append((px, py))
            
            pygame.draw.polygon(target, enemy['color'], points)
            
            # Enemy eye
            eye_size = 4
            pygame.draw.circle(target, (0, 0, 0),
                             (int(enemy['x']), int(enemy['y'])), eye_size)
        
        # Draw bullets
        for bullet in self.bullets:
            color = bullet.get('color', self.bullet_color)
            pygame.draw.rect(target, color,
                           (bullet['x'] - bullet['width'] // 2,
                            bullet['y'] - bullet['height'] // 2,
                            bullet['width'], bullet['height']))
        
        # Draw player with shield effect
        player_color = self.player_color
        if 'shield' in self.active_powers:
            # Draw shield
            shield_alpha = 100 + 155 * abs(math.sin(pygame.time.get_ticks() * 0.01))
            shield_surf = pygame.Surface((self.player_width + 20, 
                                         self.player_height + 20), 
                                        pygame.SRCALPHA)
            pygame.draw.ellipse(shield_surf, (100, 200, 255, shield_alpha),
                              (0, 0, self.player_width + 20, self.player_height + 20))
            target.blit(shield_surf, 
                       (self.player_x - (self.player_width + 20) // 2,
                        self.player_y - (self.player_height + 20) // 2))
            
            player_color = (150, 230, 255)  # Brighter when shielded
        
        # Draw player ship
        # Ship body
        ship_points = [
            (self.player_x, self.player_y - self.player_height // 2),  # Nose
            (self.player_x - self.player_width // 2, self.player_y + self.player_height // 2),  # Left wing
            (self.player_x + self.player_width // 2, self.player_y + self.player_height // 2)   # Right wing
        ]
        pygame.draw.polygon(target, player_color, ship_points)
        
        # Ship cockpit
        pygame.draw.circle(target, (50, 150, 255),
                         (int(self.player_x), int(self.player_y - 5)), 8)
        
        # Draw power-ups
        for power_up in self.power_ups:
            angle = power_up['spin']
            points = []
            for i in range(5):
                point_angle = angle + i * 2 * math.pi / 5
                px = power_up['x'] + math.cos(point_angle) * power_up['size']
                py = power_up['y'] + math.sin(point_angle) * power_up['size']
                points.append((px, py))
            
            pygame.draw.polygon(target, power_up['color'], points)
        
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
        small_font = pygame.font.Font(None, 24)
        
        # Score and wave
        score_text = font.render(f"Score: {self.score}", True, (255, 255, 255))
        wave_text = font.render(f"Wave: {self.wave}", True, (255, 255, 255))
        lives_text = font.render(f"Lives: {self.lives}", True, (255, 255, 255))
        
        surface.blit(score_text, (10, 10))
        surface.blit(wave_text, (10, 50))
        surface.blit(lives_text, (self.width - lives_text.get_width() - 10, 10))
        
        # Active power-ups
        power_y = 50
        for power_type, timer in self.active_powers.items():
            power_text = small_font.render(f"{power_type}: {timer//60}s", True, (200, 255, 200))
            surface.blit(power_text, (self.width - power_text.get_width() - 10, power_y))
            power_y += 30
        
        # Enemy count
        enemy_text = small_font.render(f"Enemies: {len(self.enemies)}", True, (255, 200, 200))
        surface.blit(enemy_text, (self.width - enemy_text.get_width() - 10, self.height - 30))
        
        # Game over screen
        if self.game_over:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surface.blit(overlay, (0, 0))
            
            game_over_font = pygame.font.Font(None, 64)
            game_over_text = game_over_font.render("GAME OVER", True, (255, 50, 50))
            final_score = font.render(f"Final Score: {self.score}", True, (255, 255, 255))
            wave_reached = font.render(f"Wave Reached: {self.wave}", True, (255, 255, 255))
            restart_text = font.render("Show UP gesture to restart", True, (100, 255, 100))
            
            surface.blit(game_over_text, (self.width // 2 - game_over_text.get_width() // 2,
                                         self.height // 2 - 80))
            surface.blit(final_score, (self.width // 2 - final_score.get_width() // 2,
                                      self.height // 2 - 20))
            surface.blit(wave_reached, (self.width // 2 - wave_reached.get_width() // 2,
                                       self.height // 2 + 20))
            surface.blit(restart_text, (self.width // 2 - restart_text.get_width() // 2,
                                       self.height // 2 + 70))
        
        # Wave complete screen
        elif not self.enemies and self.wave > 1:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            surface.blit(overlay, (0, 0))
            
            complete_font = pygame.font.Font(None, 72)
            complete_text = complete_font.render(f"WAVE {self.wave - 1} COMPLETE!", 
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