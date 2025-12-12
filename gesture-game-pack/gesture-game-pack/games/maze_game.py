"""
Maze Explorer Game with gesture-based movement
"""

import pygame
import random
import math
from game_manager import BaseGame

class MazeGame(BaseGame):
    def __init__(self, width=800, height=600):
        super().__init__(width, height)
        self.title = "Maze Explorer"
        pygame.display.set_caption(self.title)
        
        # Colors
        self.wall_color = (70, 70, 120)
        self.path_color = (30, 30, 50)
        self.player_color = (100, 200, 255)
        self.exit_color = (50, 200, 50)
        self.key_color = (255, 215, 0)
        self.enemy_color = (255, 100, 100)
        
        # Maze parameters
        self.cell_size = 40
        self.maze_width = width // self.cell_size
        self.maze_height = height // self.cell_size
        
        # Player
        self.player_x = 1
        self.player_y = 1
        
        # Game state
        self.has_key = False
        self.level = 1
        self.moves = 0
        self.enemies = []
        self.keys = []
        self.exit_pos = None
        
        # Generate first maze
        self.generate_maze()
        
        # View offset for smooth movement
        self.view_x = 0
        self.view_y = 0
        
        # Animation
        self.move_animation = None
        self.animation_progress = 0
        
        # Particles
        self.particles = []
    
    def generate_maze(self):
        """Generate a random maze using recursive backtracking"""
        self.maze = [[1 for _ in range(self.maze_width)] for _ in range(self.maze_height)]
        
        # Start position
        stack = [(1, 1)]
        self.maze[1][1] = 0
        
        directions = [(0, -2), (0, 2), (-2, 0), (2, 0)]
        
        while stack:
            x, y = stack[-1]
            random.shuffle(directions)
            
            found = False
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                
                if (0 < nx < self.maze_width - 1 and 
                    0 < ny < self.maze_height - 1 and 
                    self.maze[ny][nx] == 1):
                    
                    # Remove wall between current cell and new cell
                    wx, wy = x + dx // 2, y + dy // 2
                    self.maze[wy][wx] = 0
                    self.maze[ny][nx] = 0
                    
                    stack.append((nx, ny))
                    found = True
                    break
            
            if not found:
                stack.pop()
        
        # Place exit in bottom-right area
        exit_candidates = []
        for y in range(self.maze_height - 5, self.maze_height - 1):
            for x in range(self.maze_width - 5, self.maze_width - 1):
                if self.maze[y][x] == 0:
                    exit_candidates.append((x, y))
        
        if exit_candidates:
            self.exit_pos = random.choice(exit_candidates)
        else:
            self.exit_pos = (self.maze_width - 2, self.maze_height - 2)
        
        # Place key
        self.keys = []
        key_placed = False
        attempts = 0
        while not key_placed and attempts < 100:
            x = random.randint(1, self.maze_width - 2)
            y = random.randint(1, self.maze_height - 2)
            
            if (self.maze[y][x] == 0 and 
                (x, y) != (self.player_x, self.player_y) and
                (x, y) != self.exit_pos):
                
                self.keys.append((x, y))
                key_placed = True
            
            attempts += 1
        
        # Place enemies based on level
        self.enemies = []
        for _ in range(min(self.level, 5)):
            enemy_placed = False
            attempts = 0
            while not enemy_placed and attempts < 100:
                x = random.randint(1, self.maze_width - 2)
                y = random.randint(1, self.maze_height - 2)
                
                if (self.maze[y][x] == 0 and 
                    abs(x - self.player_x) + abs(y - self.player_y) > 10 and
                    (x, y) != self.exit_pos and
                    (x, y) not in self.keys):
                    
                    self.enemies.append({
                        'x': x,
                        'y': y,
                        'direction': random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)]),
                        'timer': random.randint(20, 60)
                    })
                    enemy_placed = True
                
                attempts += 1
    
    def handle_gesture(self, gesture_data):
        """Handle gesture input"""
        if self.move_animation is not None:
            return
        
        direction = gesture_data.get('direction')
        
        if direction:
            dx, dy = 0, 0
            
            if direction == 'UP':
                dy = -1
            elif direction == 'DOWN':
                dy = 1
            elif direction == 'LEFT':
                dx = -1
            elif direction == 'RIGHT':
                dx = 1
            
            if dx != 0 or dy != 0:
                self.attempt_move(dx, dy)
        
        # Use key with pinch
        if gesture_data.get('pinch') and self.has_key:
            # Could be used for special abilities in future
            pass
        
        # Show hint with open palm
        if gesture_data.get('open_palm'):
            self.show_hint()
    
    def attempt_move(self, dx, dy):
        """Attempt to move player"""
        new_x = self.player_x + dx
        new_y = self.player_y + dy
        
        # Check bounds and walls
        if (0 <= new_x < self.maze_width and 
            0 <= new_y < self.maze_height and 
            self.maze[new_y][new_x] == 0):
            
            # Start animation
            self.move_animation = (dx, dy)
            self.animation_progress = 0
            
            self.moves += 1
            
            # Check for key collection
            if (new_x, new_y) in self.keys:
                self.has_key = True
                self.keys.remove((new_x, new_y))
                self.create_key_particles(new_x, new_y)
            
            # Check for exit
            if (new_x, new_y) == self.exit_pos and self.has_key:
                self.level += 1
                self.has_key = False
                self.moves = 0
                self.player_x = 1
                self.player_y = 1
                self.generate_maze()
                self.create_level_up_particles()
    
    def show_hint(self):
        """Show path to exit (creates particles along path)"""
        # Simple BFS to find path
        start = (self.player_x, self.player_y)
        target = self.exit_pos
        
        queue = [start]
        visited = {start: None}
        
        while queue:
            current = queue.pop(0)
            
            if current == target:
                break
            
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = current[0] + dx, current[1] + dy
                
                if (0 <= nx < self.maze_width and 
                    0 <= ny < self.maze_height and 
                    self.maze[ny][nx] == 0 and 
                    (nx, ny) not in visited):
                    
                    visited[(nx, ny)] = current
                    queue.append((nx, ny))
        
        # Trace path back and create particles
        if target in visited:
            path = []
            current = target
            
            while current != start:
                path.append(current)
                current = visited[current]
            
            path.reverse()
            
            # Create particles along path
            for x, y in path[:10]:  # Only show first 10 steps
                self.create_hint_particle(x, y)
    
    def update(self):
        """Update game state"""
        if self.paused:
            return
        
        # Update move animation
        if self.move_animation is not None:
            self.animation_progress += 0.2
            
            if self.animation_progress >= 1:
                dx, dy = self.move_animation
                self.player_x += dx
                self.player_y += dy
                self.move_animation = None
                self.animation_progress = 0
        
        # Update enemies
        for enemy in self.enemies:
            enemy['timer'] -= 1
            
            if enemy['timer'] <= 0:
                # Change direction
                directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                enemy['direction'] = random.choice(directions)
                enemy['timer'] = random.randint(20, 60)
            
            # Try to move
            dx, dy = enemy['direction']
            new_x = enemy['x'] + dx
            new_y = enemy['y'] + dy
            
            if (0 <= new_x < self.maze_width and 
                0 <= new_y < self.maze_height and 
                self.maze[new_y][new_x] == 0):
                
                enemy['x'] = new_x
                enemy['y'] = new_y
            
            # Check collision with player
            if (enemy['x'] == self.player_x and 
                enemy['y'] == self.player_y):
                
                self.game_over = True
        
        # Update view offset for smooth scrolling
        target_view_x = self.player_x * self.cell_size - self.width // 2
        target_view_y = self.player_y * self.cell_size - self.height // 2
        
        self.view_x += (target_view_x - self.view_x) * 0.1
        self.view_y += (target_view_y - self.view_y) * 0.1
        
        # Clamp view to maze bounds
        self.view_x = max(0, min(self.view_x, 
                                self.maze_width * self.cell_size - self.width))
        self.view_y = max(0, min(self.view_y, 
                                self.maze_height * self.cell_size - self.height))
        
        # Update particles
        self.update_particles()
    
    def create_key_particles(self, x, y):
        """Create particles when collecting key"""
        for _ in range(20):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 3)
            
            particle = {
                'x': x * self.cell_size + self.cell_size // 2,
                'y': y * self.cell_size + self.cell_size // 2,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'color': self.key_color,
                'life': 30,
                'size': random.randint(2, 4)
            }
            self.particles.append(particle)
    
    def create_level_up_particles(self):
        """Create particles when leveling up"""
        for _ in range(50):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 5)
            
            particle = {
                'x': self.width // 2,
                'y': self.height // 2,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'color': (random.randint(100, 255), 
                         random.randint(100, 255), 
                         random.randint(100, 255)),
                'life': 40,
                'size': random.randint(3, 6)
            }
            self.particles.append(particle)
    
    def create_hint_particle(self, x, y):
        """Create hint particle"""
        particle = {
            'x': x * self.cell_size + self.cell_size // 2,
            'y': y * self.cell_size + self.cell_size // 2,
            'vx': 0,
            'vy': 0,
            'color': (100, 255, 100),
            'life': 60,
            'size': 4
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
        target.fill((20, 20, 40))
        
        # Calculate visible area
        start_x = max(0, int(self.view_x // self.cell_size) - 1)
        start_y = max(0, int(self.view_y // self.cell_size) - 1)
        end_x = min(self.maze_width, int((self.view_x + self.width) // self.cell_size) + 2)
        end_y = min(self.maze_height, int((self.view_y + self.height) // self.cell_size) + 2)
        
        # Draw maze
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                screen_x = x * self.cell_size - self.view_x
                screen_y = y * self.cell_size - self.view_y
                
                if self.maze[y][x] == 1:  # Wall
                    pygame.draw.rect(target, self.wall_color,
                                   (screen_x, screen_y, self.cell_size, self.cell_size))
                else:  # Path
                    pygame.draw.rect(target, self.path_color,
                                   (screen_x, screen_y, self.cell_size, self.cell_size))
        
        # Draw exit
        if self.exit_pos:
            exit_x, exit_y = self.exit_pos
            screen_x = exit_x * self.cell_size - self.view_x
            screen_y = exit_y * self.cell_size - self.view_y
            
            exit_color = self.exit_color if self.has_key else (100, 100, 100)
            pygame.draw.rect(target, exit_color,
                           (screen_x + 5, screen_y + 5,
                            self.cell_size - 10, self.cell_size - 10),
                           border_radius=5)
            
            # Draw door
            pygame.draw.rect(target, (139, 69, 19),
                           (screen_x + self.cell_size // 2 - 5, screen_y + 5,
                            10, self.cell_size - 10))
        
        # Draw keys
        for key_x, key_y in self.keys:
            screen_x = key_x * self.cell_size - self.view_x
            screen_y = key_y * self.cell_size - self.view_y
            
            # Key shape
            pygame.draw.rect(target, self.key_color,
                           (screen_x + self.cell_size // 2 - 3, screen_y + 10,
                            6, 15))
            pygame.draw.circle(target, self.key_color,
                             (screen_x + self.cell_size // 2, screen_y + 25),
                             8)
            pygame.draw.rect(target, self.path_color,
                           (screen_x + self.cell_size // 2 - 2, screen_y + 25,
                            4, 4))
        
        # Draw enemies
        for enemy in self.enemies:
            screen_x = enemy['x'] * self.cell_size - self.view_x
            screen_y = enemy['y'] * self.cell_size - self.view_y
            
            # Enemy body
            pygame.draw.circle(target, self.enemy_color,
                             (screen_x + self.cell_size // 2,
                              screen_y + self.cell_size // 2),
                             self.cell_size // 3)
            
            # Enemy eyes
            eye_offset = 5
            pygame.draw.circle(target, (0, 0, 0),
                             (screen_x + self.cell_size // 2 - eye_offset,
                              screen_y + self.cell_size // 2 - 3), 3)
            pygame.draw.circle(target, (0, 0, 0),
                             (screen_x + self.cell_size // 2 + eye_offset,
                              screen_y + self.cell_size // 2 - 3), 3)
        
        # Draw player with animation
        player_screen_x = self.player_x * self.cell_size - self.view_x
        player_screen_y = self.player_y * self.cell_size - self.view_y
        
        if self.move_animation:
            dx, dy = self.move_animation
            player_screen_x += dx * self.cell_size * (self.animation_progress - 1)
            player_screen_y += dy * self.cell_size * (self.animation_progress - 1)
        
        # Player body
        pygame.draw.circle(target, self.player_color,
                         (player_screen_x + self.cell_size // 2,
                          player_screen_y + self.cell_size // 2),
                         self.cell_size // 3)
        
        # Player eyes (look in movement direction)
        eye_dx, eye_dy = 0, -3
        if self.move_animation:
            eye_dx, eye_dy = self.move_animation
            eye_dx *= 5
            eye_dy *= 5
        
        pygame.draw.circle(target, (0, 0, 0),
                         (player_screen_x + self.cell_size // 2 + eye_dx,
                          player_screen_y + self.cell_size // 2 + eye_dy - 3), 3)
        pygame.draw.circle(target, (0, 0, 0),
                         (player_screen_x + self.cell_size // 2 + eye_dx,
                          player_screen_y + self.cell_size // 2 + eye_dy - 3), 3)
        
        # Draw particles
        for particle in self.particles:
            screen_x = particle['x'] - self.view_x
            screen_y = particle['y'] - self.view_y
            
            alpha = int(255 * (particle['life'] / 30))
            color_with_alpha = (*particle['color'], alpha)
            surf = pygame.Surface((particle['size'] * 2, particle['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color_with_alpha,
                             (particle['size'], particle['size']), particle['size'])
            target.blit(surf, (screen_x - particle['size'], screen_y - particle['size']))
        
        # Draw UI
        self.draw_ui(target)
        
        if surface is None:
            pygame.display.flip()
    
    def draw_ui(self, surface):
        """Draw user interface"""
        font = pygame.font.Font(None, 36)
        
        # Level and moves
        level_text = font.render(f"Level: {self.level}", True, (255, 255, 255))
        moves_text = font.render(f"Moves: {self.moves}", True, (255, 255, 255))
        
        surface.blit(level_text, (10, 10))
        surface.blit(moves_text, (10, 50))
        
        # Key status
        key_text = "KEY: ✓" if self.has_key else "KEY: ✗"
        key_color = (100, 255, 100) if self.has_key else (255, 100, 100)
        key_status = font.render(key_text, True, key_color)
        surface.blit(key_status, (self.width - key_status.get_width() - 10, 10))
        
        # Instructions
        inst_font = pygame.font.Font(None, 20)
        instructions = [
            "Swipe: Move through maze",
            "Open palm: Show path hint",
            "Collect key to unlock exit"
        ]
        
        for i, text in enumerate(instructions):
            inst_text = inst_font.render(text, True, (200, 200, 200))
            surface.blit(inst_text, (10, self.height - 70 + i * 20))
        
        # Game over screen
        if self.game_over:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surface.blit(overlay, (0, 0))
            
            game_over_font = pygame.font.Font(None, 64)
            game_over_text = game_over_font.render("MAZE OVERRUN", True, (255, 50, 50))
            level_text = font.render(f"Reached Level: {self.level}", True, (255, 255, 255))
            restart_text = font.render("Show UP gesture to restart", True, (100, 255, 100))
            
            surface.blit(game_over_text, (self.width // 2 - game_over_text.get_width() // 2,
                                         self.height // 2 - 60))
            surface.blit(level_text, (self.width // 2 - level_text.get_width() // 2,
                                     self.height // 2))
            surface.blit(restart_text, (self.width // 2 - restart_text.get_width() // 2,
                                       self.height // 2 + 40))
        
        # Level complete screen
        elif self.level > 1 and self.player_x == 1 and self.player_y == 1:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            surface.blit(overlay, (0, 0))
            
            complete_font = pygame.font.Font(None, 72)
            complete_text = complete_font.render(f"LEVEL {self.level - 1} COMPLETE!", 
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