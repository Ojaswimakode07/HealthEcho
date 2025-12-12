"""
Simplified Snake Game with Swipe Controls
"""

import pygame
import random
from game_manager import BaseGame

class SimpleSnakeGame(BaseGame):
    def __init__(self, width=800, height=600):
        super().__init__(width, height)
        self.title = "Simple Snake"
        
        # Game settings
        self.grid_size = 20
        self.grid_width = width // self.grid_size
        self.grid_height = height // self.grid_size
        
        # Colors
        self.bg_color = (0, 0, 0)
        self.snake_color = (0, 255, 0)
        self.food_color = (255, 0, 0)
        self.text_color = (255, 255, 255)
        
        # Game state
        self.reset()
    
    def reset(self):
        """Reset game"""
        # Snake
        start_x = self.grid_width // 2
        start_y = self.grid_height // 2
        self.snake = [(start_x, start_y), (start_x-1, start_y), (start_x-2, start_y)]
        self.direction = (1, 0)  # Right
        
        # Food
        self.spawn_food()
        
        # Game state
        self.score = 0
        self.game_over = False
        self.speed = 10  # Moves per second
        self.move_timer = 0
    
    def spawn_food(self):
        """Spawn food at random position"""
        while True:
            x = random.randint(0, self.grid_width - 1)
            y = random.randint(0, self.grid_height - 1)
            if (x, y) not in self.snake:
                self.food = (x, y)
                break
    
    def handle_swipe(self, direction):
        """Handle swipe gesture"""
        if self.game_over:
            if direction == "UP":
                self.reset()
            return
        
        # Map swipe to direction
        if direction == "UP" and self.direction != (0, 1):
            self.direction = (0, -1)
        elif direction == "DOWN" and self.direction != (0, -1):
            self.direction = (0, 1)
        elif direction == "LEFT" and self.direction != (1, 0):
            self.direction = (-1, 0)
        elif direction == "RIGHT" and self.direction != (-1, 0):
            self.direction = (1, 0)
    
    def update(self):
        """Update game state"""
        if self.paused or self.game_over:
            return
        
        # Move snake at fixed intervals
        self.move_timer += 1
        if self.move_timer < 60 // self.speed:
            return
        
        self.move_timer = 0
        
        # Move snake
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)
        
        # Check collisions
        if (new_head[0] < 0 or new_head[0] >= self.grid_width or
            new_head[1] < 0 or new_head[1] >= self.grid_height or
            new_head in self.snake):
            self.game_over = True
            return
        
        # Add new head
        self.snake.insert(0, new_head)
        
        # Check food
        if new_head == self.food:
            self.score += 10
            self.spawn_food()
        else:
            self.snake.pop()
    
    def draw(self, surface=None):
        """Draw game"""
        target = surface or self.screen
        target.fill(self.bg_color)
        
        # Draw grid
        for x in range(0, self.width, self.grid_size):
            pygame.draw.line(target, (30, 30, 30), (x, 0), (x, self.height))
        for y in range(0, self.height, self.grid_size):
            pygame.draw.line(target, (30, 30, 30), (0, y), (self.width, y))
        
        # Draw snake
        for i, (x, y) in enumerate(self.snake):
            color = (0, 200, 0) if i == 0 else self.snake_color
            rect = pygame.Rect(x*self.grid_size, y*self.grid_size, 
                             self.grid_size, self.grid_size)
            pygame.draw.rect(target, color, rect)
            pygame.draw.rect(target, (0, 100, 0), rect, 1)
        
        # Draw food
        food_rect = pygame.Rect(self.food[0]*self.grid_size, 
                               self.food[1]*self.grid_size,
                               self.grid_size, self.grid_size)
        pygame.draw.rect(target, self.food_color, food_rect)
        pygame.draw.rect(target, (150, 0, 0), food_rect, 1)
        
        # Draw UI
        font = pygame.font.Font(None, 36)
        score_text = font.render(f"Score: {self.score}", True, self.text_color)
        target.blit(score_text, (10, 10))
        
        if self.game_over:
            # Game over overlay
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            target.blit(overlay, (0, 0))
            
            game_over_font = pygame.font.Font(None, 64)
            game_over_text = game_over_font.render("GAME OVER", True, (255, 50, 50))
            final_score = font.render(f"Final Score: {self.score}", True, self.text_color)
            restart_text = font.render("Swipe UP to restart", True, (100, 255, 100))
            
            target.blit(game_over_text, (self.width//2 - game_over_text.get_width()//2, 
                                        self.height//2 - 60))
            target.blit(final_score, (self.width//2 - final_score.get_width()//2, 
                                     self.height//2))
            target.blit(restart_text, (self.width//2 - restart_text.get_width()//2, 
                                      self.height//2 + 40))
        
        if surface is None:
            pygame.display.flip()
    
    def get_surface(self):
        """Get game surface"""
        surf = pygame.Surface((self.width, self.height))
        self.draw(surf)
        return surf