import pygame
import random
import math
import time

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BACKGROUND_COLOR = (10, 10, 10)  # Dark background
CIGARETTE_COLOR = (255, 255, 240)  # Off-white for cigarette paper
FILTER_COLOR = (210, 180, 140)  # Tan color for filter
TOBACCO_COLOR = (255, 255, 240)  # White for tobacco
BURNING_COLOR = (255, 100, 0)  # Orange for burning tip
ASH_COLOR = (128, 128, 128)  # Gray for ash
SMOKE_COLOR = (200, 200, 200)  # Light gray for smoke


class SmokeParticle:

    def __init__(self, x, y):
        self.x = x + random.uniform(-2, 2)
        self.y = y
        self.vel_x = random.uniform(-0.5, 0.5)
        self.vel_y = random.uniform(-0.5, -1)
        self.life = 100
        self.max_life = 100
        self.size = random.uniform(1, 3)
        
    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        self.vel_y -= 0.01  # Slight upward acceleration
        self.life -= 1
        
        # Add some randomness to movement
        self.vel_x += random.uniform(-0.01, 0.01)
        self.vel_y += random.uniform(-0.05, 0.05)
        
    def draw(self, screen):
        if self.life > 0:
            alpha = int(255 * (self.life / self.max_life))
            color = (*SMOKE_COLOR, alpha)
            
            # Create a surface for the smoke particle with alpha
            smoke_surface = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(smoke_surface, color, (int(self.size), int(self.size)), int(self.size))
            screen.blit(smoke_surface, (int(self.x - self.size), int(self.y - self.size)))
            
    def is_dead(self):
        return self.life <= 0


class Cigarette:

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.length = 120  # Total cigarette length
        self.filter_length = 20  # Filter length
        self.width = 8
        self.burn_position = 0  # How much has burned (0 = not started, length = fully burned)
        self.is_lit = False
        self.burn_speed = 0.010  # Slower burning for peaceful effect
        self.ash_particles = []
        self.smoke_particles = []
        self.ember_intensity = 0
        self.last_ash_time = 0
        self.start_time = time.time()
        
    def update(self):
        # Auto-light after 2 seconds
        if not self.is_lit and time.time() - self.start_time > 2:
            self.is_lit = True
            
        if self.is_lit and self.burn_position < self.length - self.filter_length:
            self.burn_position += self.burn_speed
            
            # Create smoke particles
            if random.random() < 0.3:  # 30% chance each frame
                tip_x = self.x + self.burn_position
                tip_y = self.y + self.width // 2
                self.smoke_particles.append(SmokeParticle(tip_x, tip_y))
            
            # Create ash particles occasionally
            if random.random() < 0.02 and time.time() - self.last_ash_time > 2:  # Every few seconds
                self.create_ash_particle()
                self.last_ash_time = time.time()
            
            # Update ember intensity (pulsing effect)
            self.ember_intensity = 0.5 + 0.5 * math.sin(time.time() * 10)
        
        # Update smoke particles
        for particle in self.smoke_particles[:]:
            particle.update()
            if particle.is_dead():
                self.smoke_particles.remove(particle)
        
        # Update ash particles
        for ash in self.ash_particles[:]:
            ash['y'] += ash['vel_y']
            ash['vel_y'] += 0.1  # Gravity
            ash['life'] -= 1
            if ash['life'] <= 0:
                self.ash_particles.remove(ash)
                
    def create_ash_particle(self):
        for _ in range(random.randint(3, 8)):
            ash = {
                'x': self.x + self.burn_position + random.uniform(-5, 5),
                'y': self.y + self.width // 2 + random.uniform(-2, 2),
                'vel_y': random.uniform(-1, 1),
                'life': random.randint(60, 120),
                'size': random.uniform(1, 2)
            }
            self.ash_particles.append(ash)
    
    def draw(self, screen):
        # Draw unburned cigarette (white paper)
        unburned_length = self.length - self.burn_position
        if unburned_length > 0:
            cigarette_rect = pygame.Rect(
                self.x + self.burn_position, 
                self.y, 
                unburned_length - self.filter_length, 
                self.width
            )
            pygame.draw.rect(screen, CIGARETTE_COLOR, cigarette_rect)
            
            # Draw tobacco inside (slightly smaller)
            tobacco_rect = pygame.Rect(
                self.x + self.burn_position + 1, 
                self.y + 1, 
                max(0, unburned_length - self.filter_length - 2), 
                self.width - 2
            )
            if tobacco_rect.width > 0:
                pygame.draw.rect(screen, TOBACCO_COLOR, tobacco_rect)
        
        # Draw filter
        filter_rect = pygame.Rect(
            self.x + self.length - self.filter_length, 
            self.y, 
            self.filter_length, 
            self.width
        )
        pygame.draw.rect(screen, FILTER_COLOR, filter_rect)
        
        # Draw burning tip
        if self.is_lit and self.burn_position < self.length - self.filter_length:
            tip_x = self.x + self.burn_position
            
            # Burning ember (pulsing effect)
            ember_color = (
                int(255 * self.ember_intensity),
                int(100 * self.ember_intensity),
                0
            )
            ember_rect = pygame.Rect(tip_x - 2, self.y, 4, self.width)
            pygame.draw.rect(screen, ember_color, ember_rect)
            
            # Inner bright spot
            inner_rect = pygame.Rect(tip_x - 1, self.y + 1, 2, self.width - 2)
            pygame.draw.rect(screen, (255, 255, 100), inner_rect)
        
        # Draw ash particles
        for ash in self.ash_particles:
            pygame.draw.circle(screen, ASH_COLOR, 
                             (int(ash['x']), int(ash['y'])), 
                             int(ash['size']))
        
        # Draw smoke particles
        for particle in self.smoke_particles:
            particle.draw(screen)
        
        # Draw ash buildup at the tip
        if self.burn_position > 10:
            ash_length = min(15, self.burn_position * 0.3)
            ash_rect = pygame.Rect(
                self.x + self.burn_position - ash_length,
                self.y,
                ash_length,
                self.width
            )
            pygame.draw.rect(screen, ASH_COLOR, ash_rect)


class CigaretteSimulator:

    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Cigarette")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Create cigarette positioned in center
        self.cigarette = Cigarette(SCREEN_WIDTH // 2 - 60, SCREEN_HEIGHT // 2 - 4)
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
    
    def update(self):
        self.cigarette.update()
    
    def draw(self):
        self.screen.fill(BACKGROUND_COLOR)
        
        # Draw cigarette
        self.cigarette.draw(self.screen)
        
        pygame.display.flip()
    
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)  # 60 FPS
        
        pygame.quit()

if __name__ == "__main__":
    simulator = CigaretteSimulator()
    simulator.run()
