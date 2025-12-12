"""
Tetris Game with gesture controls
"""

import pygame
import random
import math
from game_manager import BaseGame

class TetrisGame(BaseGame):
    def __init__(self, width=800, height=600):
        super().__init__(width, height)
        self.title = "Tetris"
        pygame.display.set_caption(self.title)
        
        # Game grid
        self.grid_width = 10
        self.grid_height = 20
        self.cell_size = 30
        
        # Calculate game area position
        self.game_x = (width - (self.grid_width * self.cell_size)) // 2
        self.game_y = (height - (self.grid_height * self.cell_size)) // 2
        
        # Colors
        self.bg_color = (20, 20, 40)
        self.grid_color = (50, 50, 80)
        self.empty_color = (30, 30, 60)
        
        # Tetromino colors
        self.colors = [
            (0, 255, 255),    # I - Cyan
            (0, 0, 255),      # J - Blue
            (255, 165, 0),    # L - Orange
            (255, 255, 0),    # O - Yellow
            (0, 255, 0),      # S - Green
            (128, 0, 128),    # T - Purple
            (255, 0, 0)       # Z - Red
        ]
        
        # Tetromino shapes
        self.shapes = [
            [[1, 1, 1, 1]],  # I
            [[1, 0, 0], [1, 1, 1]],  # J
            [[0, 0, 1], [1, 1, 1]],  # L
            [[1, 1], [1, 1]],  # O
            [[0, 1, 1], [1, 1, 0]],  # S
            [[0, 1, 0], [1, 1, 1]],  # T
            [[1, 1, 0], [0, 1, 1]]   # Z
        ]
        
        # Game state
        self.grid = [[0 for _ in range(self.grid_width)] for _ in range(self.grid_height)]
        self.current_piece = None
        self.next_piece = None
        self.piece_x = 0
        self.piece_y = 0
        self.fall_speed = 1.0
        self.fall_timer = 0
        
        # Score
        self.level = 1
        self.lines_cleared = 0
        
        # Ghost piece
        self.show_ghost = True
        
        # Hold piece
        self.hold_piece = None
        self.can_hold = True
        
        # Initialize
        self.new_piece()
        self.next_piece = self.get_random_piece()
        
        # Particles
        self.particles = []
    
    def get_random_piece(self):
        """Get a random tetromino"""
        shape_idx = random.randint(0, len(self.shapes) - 1)
        return {
            'shape': self.shapes[shape_idx],
            'color': self.colors[shape_idx],
            'rotation': 0
        }
    
    def new_piece(self):
        """Create a new falling piece"""
        if self.next_piece:
            self.current_piece = self.next_piece
            self.next_piece = self.get_random_piece()
        else:
            self.current_piece = self.get_random_piece()
        
        self.piece_x = self.grid_width // 2 - len(self.current_piece['shape'][0]) // 2
        self.piece_y = 0
        self.can_hold = True
        
        # Check if game over (new piece can't be placed)
        if self.check_collision(self.piece_x, self.piece_y, self.current_piece['shape']):
            self.game_over = True
    
    def rotate_piece(self, clockwise=True):
        """Rotate the current piece"""
        shape = self.current_piece['shape']
        rotated = []
        
        if clockwise:
            # Transpose and reverse each row
            for col in range(len(shape[0])):
                new_row = []
                for row in range(len(shape) - 1, -1, -1):
                    new_row.append(shape[row][col])
                rotated.append(new_row)
        else:
            # Reverse each row and transpose
            for col in range(len(shape[0]) - 1, -1, -1):
                new_row = []
                for row in range(len(shape)):
                    new_row.append(shape[row][col])
                rotated.append(new_row)
        
        # Check if rotation is valid
        if not self.check_collision(self.piece_x, self.piece_y, rotated):
            self.current_piece['shape'] = rotated
            self.current_piece['rotation'] = (self.current_piece['rotation'] + (1 if clockwise else -1)) % 4
    
    def check_collision(self, x, y, shape):
        """Check if piece collides with walls or other pieces"""
        for row_idx, row in enumerate(shape):
            for col_idx, cell in enumerate(row):
                if cell:
                    grid_x = x + col_idx
                    grid_y = y + row_idx
                    
                    if (grid_x < 0 or grid_x >= self.grid_width or
                        grid_y >= self.grid_height or
                        (grid_y >= 0 and self.grid[grid_y][grid_x])):
                        return True
        return False
    
    def place_piece(self):
        """Place the current piece on the grid"""
        shape = self.current_piece['shape']
        color = self.current_piece['color']
        
        for row_idx, row in enumerate(shape):
            for col_idx, cell in enumerate(row):
                if cell:
                    grid_x = self.piece_x + col_idx
                    grid_y = self.piece_y + row_idx
                    
                    if 0 <= grid_y < self.grid_height:
                        self.grid[grid_y][grid_x] = color
        
        # Check for completed lines
        self.check_lines()
        
        # Create new piece
        self.new_piece()
    
    def check_lines(self):
        """Check and clear completed lines"""
        lines_to_clear = []
        
        for row in range(self.grid_height):
            if all(self.grid[row]):
                lines_to_clear.append(row)
        
        if lines_to_clear:
            # Add to score
            self.lines_cleared += len(lines_to_clear)
            self.score += [100, 300, 500, 800][min(len(lines_to_clear) - 1, 3)] * self.level
            
            # Create line clear particles
            for line in lines_to_clear:
                self.create_line_clear_particles(line)
            
            # Clear lines
            for line in sorted(lines_to_clear):
                del self.grid[line]
                self.grid.insert(0, [0 for _ in range(self.grid_width)])
            
            # Increase level
            self.level = 1 + self.lines_cleared // 10
            self.fall_speed = min(2.0, 1.0 + (self.level - 1) * 0.1)
    
    def hold_current_piece(self):
        """Hold the current piece"""
        if not self.can_hold:
            return
        
        if self.hold_piece is None:
            self.hold_piece = self.current_piece
            self.new_piece()
        else:
            self.hold_piece, self.current_piece = self.current_piece, self.hold_piece
            self.piece_x = self.grid_width // 2 - len(self.current_piece['shape'][0]) // 2
            self.piece_y = 0
        
        self.can_hold = False
    
    def get_ghost_y(self):
        """Get ghost piece position (where piece would land)"""
        ghost_y = self.piece_y
        
        while not self.check_collision(self.piece_x, ghost_y + 1, self.current_piece['shape']):
            ghost_y += 1
        
        return ghost_y
    
    def handle_gesture(self, gesture_data):
        """Handle gesture input"""
        direction = gesture_data.get('direction')
        
        if direction == 'LEFT':
            if not self.check_collision(self.piece_x - 1, self.piece_y, self.current_piece['shape']):
                self.piece_x -= 1
        
        elif direction == 'RIGHT':
            if not self.check_collision(self.piece_x + 1, self.piece_y, self.current_piece['shape']):
                self.piece_x += 1
        
        elif direction == 'DOWN':
            if not self.check_collision(self.piece_x, self.piece_y + 1, self.current_piece['shape']):
                self.piece_y += 1
            else:
                self.place_piece()
        
        elif direction == 'UP':
            self.rotate_piece(clockwise=True)
        
        # Hard drop with pinch
        if gesture_data.get('pinch'):
            ghost_y = self.get_ghost_y()
            self.piece_y = ghost_y
            self.place_piece()
        
        # Hold piece with open palm
        if gesture_data.get('open_palm'):
            self.hold_current_piece()
    
    def update(self):
        """Update game state"""
        if self.paused or self.game_over:
            return
        
        # Update fall timer
        self.fall_timer += self.fall_speed
        
        if self.fall_timer >= 60:  # 60 frames per "tick"
            self.fall_timer = 0
            
            # Move piece down
            if not self.check_collision(self.piece_x, self.piece_y + 1, self.current_piece['shape']):
                self.piece_y += 1
            else:
                self.place_piece()
        
        # Update particles
        self.update_particles()
    
    def create_line_clear_particles(self, line):
        """Create particles when clearing a line"""
        for col in range(self.grid_width):
            x = self.game_x + col * self.cell_size + self.cell_size // 2
            y = self.game_y + line * self.cell_size + self.cell_size // 2
            
            for _ in range(5):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(1, 4)
                
                particle = {
                    'x': x,
                    'y': y,
                    'vx': math.cos(angle) * speed,
                    'vy': math.sin(angle) * speed,
                    'color': self.grid[line][col] if self.grid[line][col] else (255, 255, 255),
                    'life': 30,
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
        
        # Draw game area background
        pygame.draw.rect(target, (30, 30, 60),
                        (self.game_x - 10, self.game_y - 10,
                         self.grid_width * self.cell_size + 20,
                         self.grid_height * self.cell_size + 20),
                        border_radius=10)
        
        # Draw grid
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                cell_x = self.game_x + x * self.cell_size
                cell_y = self.game_y + y * self.cell_size
                
                # Draw cell
                color = self.grid[y][x] if self.grid[y][x] else self.empty_color
                pygame.draw.rect(target, color,
                                (cell_x + 1, cell_y + 1,
                                 self.cell_size - 2, self.cell_size - 2),
                                border_radius=2)
                
                # Draw grid lines
                pygame.draw.rect(target, self.grid_color,
                                (cell_x, cell_y, self.cell_size, self.cell_size), 1)
        
        if not self.game_over:
            # Draw ghost piece
            if self.show_ghost:
                ghost_y = self.get_ghost_y()
                shape = self.current_piece['shape']
                color = self.current_piece['color']
                ghost_color = (color[0]//3, color[1]//3, color[2]//3)  # Darker version
                
                for row_idx, row in enumerate(shape):
                    for col_idx, cell in enumerate(row):
                        if cell:
                            cell_x = self.game_x + (self.piece_x + col_idx) * self.cell_size
                            cell_y = self.game_y + (ghost_y + row_idx) * self.cell_size
                            
                            pygame.draw.rect(target, ghost_color,
                                           (cell_x + 1, cell_y + 1,
                                            self.cell_size - 2, self.cell_size - 2),
                                           border_radius=2)
            
            # Draw current piece
            shape = self.current_piece['shape']
            color = self.current_piece['color']
            
            for row_idx, row in enumerate(shape):
                for col_idx, cell in enumerate(row):
                    if cell:
                        cell_x = self.game_x + (self.piece_x + col_idx) * self.cell_size
                        cell_y = self.game_y + (self.piece_y + row_idx) * self.cell_size
                        
                        # Draw piece with 3D effect
                        pygame.draw.rect(target, color,
                                       (cell_x + 1, cell_y + 1,
                                        self.cell_size - 2, self.cell_size - 2),
                                       border_radius=3)
                        
                        # Draw highlight
                        highlight = (min(255, color[0] + 50),
                                   min(255, color[1] + 50),
                                   min(255, color[2] + 50))
                        pygame.draw.rect(target, highlight,
                                       (cell_x + 3, cell_y + 3,
                                        self.cell_size - 6, self.cell_size // 4),
                                       border_radius=1)
        
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
        # Next piece preview
        next_x = self.game_x + self.grid_width * self.cell_size + 30
        next_y = self.game_y
        
        pygame.draw.rect(surface, (40, 40, 70),
                        (next_x - 10, next_y - 10, 130, 130),
                        border_radius=10)
        
        title_font = pygame.font.Font(None, 24)
        next_text = title_font.render("NEXT", True, (200, 200, 255))
        surface.blit(next_text, (next_x + 45, next_y))
        
        if self.next_piece:
            shape = self.next_piece['shape']
            color = self.next_piece['color']
            
            for row_idx, row in enumerate(shape):
                for col_idx, cell in enumerate(row):
                    if cell:
                        cell_x = next_x + col_idx * self.cell_size + 20
                        cell_y = next_y + row_idx * self.cell_size + 30
                        
                        pygame.draw.rect(surface, color,
                                       (cell_x, cell_y,
                                        self.cell_size - 4, self.cell_size - 4),
                                       border_radius=2)
        
        # Hold piece
        hold_x = self.game_x - 140
        hold_y = self.game_y
        
        pygame.draw.rect(surface, (40, 40, 70),
                        (hold_x - 10, hold_y - 10, 130, 130),
                        border_radius=10)
        
        hold_text = title_font.render("HOLD", True, (200, 200, 255))
        surface.blit(hold_text, (hold_x + 45, hold_y))
        
        if self.hold_piece:
            shape = self.hold_piece['shape']
            color = self.hold_piece['color']
            
            for row_idx, row in enumerate(shape):
                for col_idx, cell in enumerate(row):
                    if cell:
                        cell_x = hold_x + col_idx * self.cell_size + 20
                        cell_y = hold_y + row_idx * self.cell_size + 30
                        
                        pygame.draw.rect(surface, color,
                                       (cell_x, cell_y,
                                        self.cell_size - 4, self.cell_size - 4),
                                       border_radius=2)
        
        # Score and stats
        font = pygame.font.Font(None, 36)
        small_font = pygame.font.Font(None, 24)
        
        stats_y = self.game_y + 150
        
        score_text = font.render(f"Score: {self.score}", True, (255, 255, 255))
        level_text = font.render(f"Level: {self.level}", True, (255, 255, 255))
        lines_text = font.render(f"Lines: {self.lines_cleared}", True, (255, 255, 255))
        
        surface.blit(score_text, (self.game_x, stats_y))
        surface.blit(level_text, (self.game_x, stats_y + 40))
        surface.blit(lines_text, (self.game_x, stats_y + 80))
        
        # Controls
        controls_y = self.game_y + self.grid_height * self.cell_size - 100
        controls = [
            "Swipe LEFT/RIGHT: Move",
            "Swipe UP: Rotate",
            "Swipe DOWN: Soft drop",
            "Pinch: Hard drop",
            "Open palm: Hold piece"
        ]
        
        for i, text in enumerate(controls):
            control_text = small_font.render(text, True, (200, 200, 200))
            surface.blit(control_text, (self.game_x, controls_y + i * 20))
        
        # Game over screen
        if self.game_over:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surface.blit(overlay, (0, 0))
            
            game_over_font = pygame.font.Font(None, 64)
            game_over_text = game_over_font.render("GAME OVER", True, (255, 50, 50))
            final_score = font.render(f"Final Score: {self.score}", True, (255, 255, 255))
            lines_cleared = font.render(f"Lines Cleared: {self.lines_cleared}", True, (255, 255, 255))
            level_reached = font.render(f"Level Reached: {self.level}", True, (255, 255, 255))
            restart_text = font.render("Show UP gesture to restart", True, (100, 255, 100))
            
            surface.blit(game_over_text, (self.width // 2 - game_over_text.get_width() // 2,
                                         self.height // 2 - 100))
            surface.blit(final_score, (self.width // 2 - final_score.get_width() // 2,
                                      self.height // 2 - 40))
            surface.blit(lines_cleared, (self.width // 2 - lines_cleared.get_width() // 2,
                                        self.height // 2))
            surface.blit(level_reached, (self.width // 2 - level_reached.get_width() // 2,
                                        self.height // 2 + 40))
            surface.blit(restart_text, (self.width // 2 - restart_text.get_width() // 2,
                                       self.height // 2 + 100))
        
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