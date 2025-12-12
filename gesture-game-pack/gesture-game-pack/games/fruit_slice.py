"""
Simplified Fruit Slice Game - Horizontal Swipes Only
"""

import pygame
import random
import math
from game_manager import BaseGame

class SimpleFruitSlice(BaseGame):
    def __init__(self, width=800, height=600):
        super().__init__(width, height)
        self.title = "Fruit Slice"
        
        # Colors
        self.bg_color = (135, 206, 235)  # Sky blue
        self.slice_color = (255, 255, 255)
        
        # Fruits
        self.fruits = []
        self.fruit_colors = [
            (255, 50, 50),    # Red apple
            (255, 165, 0),    # Orange
            (255, 255, 100),  # Yellow banana
            (100, 200, 100),  # Green watermelon
            (255, 100, 150),  # Pink strawberry
        ]
        
        # Game state
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        
        # Slice effect
        self.slice_lines = []
        
        # Spawn timer
        self.spawn_timer = 0
        
        # Particles for effects
        self.particles = []
    
    def handle_swipe(self, direction):
        """Handle horizontal swipes only"""
        if direction in ["LEFT", "RIGHT"]:
            self.create_slice(direction)
    
    def create_slice(self, direction):
        """Create a slice line across screen"""
        if direction == "LEFT":
            # Slice from right to left
            self.slice_lines.append({
                'x1': self.width,
                'y1': self.height // 2,
                'x2': 0,
                'y2': self.height // 2,
                'life': 30
            })
        else:  # RIGHT
            # Slice from left to right
            self.slice_lines.append({
                'x1': 0,
                'y1': self.height // 2,
                'x2': self.width,
                'y2': self.height // 2,
                'life': 30
            })
        
        # Check for fruit slices
        self.check_slices()
    
    def check_slices(self):
        """Check if slice lines intersect fruits"""
        if not self.slice_lines:
            return
        
        current_slice = self.slice_lines[-1]
        
        for fruit in self.fruits[:]:
            # Simple collision check (fruit near slice line)
            slice_y = current_slice['y1']
            fruit_y = fruit['y']
            
            if abs(fruit_y - slice_y) < fruit['radius']:
                # Fruit sliced!
                self.score += 10
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
                
                # Create particles
                self.create_slice_particles(fruit)
                
                # Remove fruit
                self.fruits.remove(fruit)
                
                # Combo bonus
                if self.combo >= 3:
                    self.score += (self.combo - 2) * 5
    
    def spawn_fruit(self):
        """Spawn a new fruit"""
        fruit_type = random.randint(0, len(self.fruit_colors) - 1)
        
        fruit = {
            'x': random.randint(50, self.width - 50),
            'y': self.height + 50,  # Start below screen
            'radius': random.randint(20, 40),
            'color': self.fruit_colors[fruit_type],
            'vy': random.uniform(-8, -4),  # Upward velocity
            'vx': random.uniform(-2, 2),   # Horizontal drift
        }
        
        self.fruits.append(fruit)
    
    def create_slice_particles(self, fruit):
        """Create particles when slicing fruit"""
        for _ in range(15):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 4)
            
            particle = {
                'x': fruit['x'],
                'y': fruit['y'],
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'color': fruit['color'],
                'life': 30,
                'size': random.randint(2, 5)
            }
            self.particles.append(particle)
    
    def update(self):
        """Update game state"""
        if self.paused:
            return
        
        # Spawn fruits
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_fruit()
            self.spawn_timer = random.randint(30, 90)
        
        # Update fruits
        for fruit in self.fruits[:]:
            fruit['x'] += fruit['vx']
            fruit['y'] += fruit['vy']
            fruit['vy'] += 0.2  # Gravity
            
            # Remove off-screen fruits
            if fruit['y'] > self.height + 100:
                self.fruits.remove(fruit)
                self.combo = 0  # Reset combo
        
        # Update slice lines
        for line in self.slice_lines[:]:
            line['life'] -= 1
            if line['life'] <= 0:
                self.slice_lines.remove(line)
        
        # Update particles
        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['vy'] += 0.1  # Gravity
            particle['life'] -= 1
            
            if particle['life'] <= 0:
                self.particles.remove(particle)
    
    def draw(self, surface=None):
        """Draw game"""
        target = surface or self.screen
        target.fill(self.bg_color)
        
        # Draw ground
        pygame.draw.rect(target, (100, 200, 100),
                        (0, self.height - 50, self.width, 50))
        
        # Draw fruits
        for fruit in self.fruits:
            pygame.draw.circle(target, fruit['color'],
                             (int(fruit['x']), int(fruit['y'])),
                             fruit['radius'])
            
            # Draw shine
            pygame.draw.circle(target, (255, 255, 255, 128),
                             (int(fruit['x'] - fruit['radius']//3), 
                              int(fruit['y'] - fruit['radius']//3)),
                             fruit['radius']//4)
        
        # Draw slice lines
        for line in self.slice_lines:
            alpha = int(255 * (line['life'] / 30))
            pygame.draw.line(target, (*self.slice_color, alpha),
                           (line['x1'], line['y1']),
                           (line['x2'], line['y2']), 3)
        
        # Draw particles
        for particle in self.particles:
            alpha = int(255 * (particle['life'] / 30))
            color_with_alpha = (*particle['color'], alpha)
            pygame.draw.circle(target, color_with_alpha,
                             (int(particle['x']), int(particle['y'])),
                             particle['size'])
        
        # Draw UI
        font = pygame.font.Font(None, 36)
        score_text = font.render(f"Score: {self.score}", True, (255, 255, 255))
        combo_text = font.render(f"Combo: {self.combo}", True, (255, 255, 0))
        max_combo_text = font.render(f"Max Combo: {self.max_combo}", True, (200, 200, 200))
        
        target.blit(score_text, (10, 10))
        target.blit(combo_text, (10, 50))
        target.blit(max_combo_text, (10, 90))
        
        # Instructions
        inst_font = pygame.font.Font(None, 24)
        inst_text = inst_font.render("Swipe LEFT/RIGHT to slice fruits", 
                                    True, (255, 255, 255))
        target.blit(inst_text, (self.width//2 - inst_text.get_width()//2, self.height - 30))
        
        if surface is None:
            pygame.display.flip()
    
    def get_surface(self):
        """Get game surface"""
        surf = pygame.Surface((self.width, self.height))
        self.draw(surf)
        return surf