import pygame
import numpy as np
import asyncio
import platform
import random
import math

# Initialize Pygame
pygame.init()
FPS = 60

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Realistic Fire Simulation with Flame Shape")

# Fire parameters
PARTICLE_COUNT = 5000  # More particles for a fuller flame
FLAME_BASE_WIDTH = 100  # Pixel width of the fire source
FLAME_CENTER = WIDTH // 2

# Volumetric fire parameters
FIRE_VOLUME_HEIGHT = 100  # Height of the burning volume
FIRE_VOLUME_DEPTH = 80   # Simulated depth of the fire volume
EMISSION_ZONES = 3       # Number of different emission zones

# Turbulence parameters
TURBULENCE_STRENGTH = 40.0  # How strong the turbulent forces are
TURBULENCE_FREQUENCY = 0.02  # How frequent the turbulent patterns are
NOISE_SCALE = 0.02  # Scale for noise function

# Colors for temperature gradient (RGBA for transparency)
COLORS = [
    (139, 0, 0, 120),     # Dark red (coolest, ~500°C)
    (178, 34, 34, 140),   # Firebrick red
    (220, 20, 60, 150),   # Crimson
    (255, 0, 0, 160),     # Pure red (~600°C)
    (255, 69, 0, 170),    # Red-orange
    (255, 99, 71, 180),   # Tomato
    (255, 140, 0, 190),   # Dark orange
    (255, 165, 0, 200),   # Orange (~800°C)
    (255, 200, 0, 210),   # Golden orange
    (255, 215, 0, 220),   # Gold
    (255, 255, 0, 230),   # Yellow (~1000°C)
    (255, 255, 100, 240), # Light yellow
    (255, 255, 150, 250), # Pale yellow
    (255, 255, 200, 255), # Near-white (~1200°C)
    (255, 255, 255, 255), # White hot (~1500°C+)
]

# Particle list
particles = []

# Time accumulator for turbulence
time_offset = 0.0


def simple_noise(x, y, time):
    """Simple pseudo-noise function for turbulence"""
    return (math.sin(x * NOISE_SCALE + time) * 
            math.cos(y * NOISE_SCALE + time * 0.7) * 
            math.sin((x + y) * NOISE_SCALE * 0.5 + time * 1.3))


def get_turbulent_force(x, y, time):
    """Calculate turbulent force at given position and time"""
    # Multiple noise layers for more complex turbulence
    noise1 = simple_noise(x, y, time)
    noise2 = simple_noise(x * 2, y * 2, time * 1.5) * 0.5
    noise3 = simple_noise(x * 4, y * 4, time * 2.0) * 0.25
    
    combined_noise = noise1 + noise2 + noise3
    
    # Convert noise to force vectors
    force_x = combined_noise * TURBULENCE_STRENGTH * 0.8
    force_y = simple_noise(x + 100, y + 100, time) * TURBULENCE_STRENGTH
    
    return force_x, force_y


# Fire particle class
class Particle:
    def __init__(self, x, y, temp, emission_zone=0):
        self.x = x
        self.y = y
        self.temp = temp  # Temperature (0 to 1)
        self.emission_zone = emission_zone  # Which zone this particle came from
        
        # Volumetric emission - particles can go in various directions
        if emission_zone == 0:  # Core burning zone - probabilistically favors upward
            # Use a normal distribution centered on straight up (-π/2)
            # Most particles go upward, but some can go at angles
            base_angle = -math.pi/2  # Straight up
            angle_variance = math.pi/12  # ±15 degrees standard deviation
            angle = random.gauss(base_angle, angle_variance)
            
            # Calculate speed based on temperature (hotter = faster)
            # But give cooler particles enough speed to travel and be visible
            base_speed = temp * 200.0 + 80.0  # Speed range: 80-280 (higher minimum)
            speed_variation = random.uniform(0.8, 1.2)  # ±20% variation
            speed = base_speed * speed_variation
            
            self.vx = speed * math.cos(angle) + random.uniform(-3.0, 3.0)
            self.vy = speed * math.sin(angle)
            
        elif emission_zone == 1:  # Mid-zone - favors angled emissions
            # Use a bimodal distribution favoring -75° and -105° (angled upward)
            if random.random() < 0.5:
                base_angle = -math.pi*5/12  # -75°
            else:
                base_angle = -math.pi*7/12  # -105°
            
            angle_variance = math.pi/8  # ±22.5 degrees standard deviation
            angle = random.gauss(base_angle, angle_variance)
            
            # Clamp to reasonable range (-π/4 to -3π/4, i.e., -45° to -135°)
            angle = max(-3*math.pi/4, min(-math.pi/4, angle))
            
            # Temperature-based speed
            base_speed = temp * 150.0 + 60.0  # Speed range: 60-210 (higher minimum)
            speed_variation = random.uniform(0.8, 1.2)
            speed = base_speed * speed_variation
            
            self.vx = speed * math.cos(angle) + random.uniform(-10.0, 10.0)
            self.vy = speed * math.sin(angle)
            
        else:  # Outer zone - broader lateral distribution
            # Use a flatter distribution centered around -90° but with wider spread
            base_angle = -math.pi/2  # -90° (straight up)
            angle_variance = math.pi/4  # ±45 degrees standard deviation (wider than core)
            angle = random.gauss(base_angle, angle_variance)
            
            # Allow wider range (-π/6 to -5π/6, i.e., -30° to -150°)
            # But with additional probability for more lateral angles
            if random.random() < 0.3:  # 30% chance for more lateral emission
                if random.random() < 0.5:
                    angle = random.uniform(-math.pi/6, -math.pi/3)  # -30° to -60°
                else:
                    angle = random.uniform(-2*math.pi/3, -5*math.pi/6)  # -120° to -150°
            else:
                # Clamp the gaussian to normal range
                angle = max(-5*math.pi/6, min(-math.pi/6, angle))
            
            # Temperature-based speed (cooler outer zone)
            base_speed = temp * 100.0 + 50.0  # Speed range: 50-150 (higher minimum)
            speed_variation = random.uniform(0.8, 1.2)
            speed = base_speed * speed_variation
            
            self.vx = speed * math.cos(angle) + random.uniform(-15.0, 15.0)
            self.vy = speed * math.sin(angle)
        
        self.life = random.uniform(1.5, 3.0)  # Longer lifespan
        self.age = 0
        self.turbulence_sensitivity = random.uniform(2.5, 3.5)  # How much particle responds to turbulence
        self.initial_size = random.uniform(4.0, 5.0)  # Starting size
        self.max_size = random.uniform(6.0, 7.0)  # Maximum size during expansion
        self.current_size = self.initial_size
        
        # Depth simulation (for layering effect)
        self.depth = random.uniform(0.0, 1.0)  # 0 = front, 1 = back

    def update(self, dt):
        global time_offset
        
        # Apply turbulent forces
        turb_x, turb_y = get_turbulent_force(self.x, self.y, time_offset)
        self.vx += turb_x * dt * self.turbulence_sensitivity
        self.vy += turb_y * dt * self.turbulence_sensitivity
        
        # Apply velocity damping to prevent particles from going too wild
        self.vx *= 0.98
        self.vy *= 0.99
        
        # Apply buoyancy - hotter particles rise faster
        buoyancy_force = self.temp * 20.0  # Stronger buoyancy for hotter particles
        self.vy -= buoyancy_force * dt
        
        # Apply temperature-based deceleration (particles slow down as they cool)
        temp_decay_factor = 0.98 + (self.temp * 0.02)  # Range: 0.95-1.0 based on temperature
        self.vx *= temp_decay_factor
        self.vy *= temp_decay_factor
        
        # Update position
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Add some random swirling motion
        swirl_force = math.sin(self.age * 3.0 + self.x * 0.01) * 2.0
        self.vx += swirl_force * dt
        
        self.age += dt
        self.temp -= dt * 0.3  # Slower cooling
        
        # Update particle size based on age and temperature
        # Particles expand in the first half of their life, then may shrink as they cool
        life_progress = self.age / self.life
        if life_progress < 0.4:  # Expansion phase
            expansion_factor = life_progress / 0.4  # 0 to 1
            self.current_size = self.initial_size + (self.max_size - self.initial_size) * expansion_factor
        else:  # Cooling/shrinking phase
            shrink_progress = (life_progress - 0.4) / 0.6  # 0 to 1
            # Shrink based on temperature loss
            temp_factor = max(0.3, self.temp)  # Don't shrink below 30% of max size
            self.current_size = self.max_size * temp_factor
        
        return self.temp > 0 and self.age < self.life and 0 <= self.y < HEIGHT

    def draw(self, surface):
        if self.temp > 0:
            # More accurate temperature-to-color mapping
            # Apply non-linear mapping to shift to red faster
            temp_normalized = max(0, min(1, self.temp))  # Ensure 0-1 range
            
            # Apply power function to make color shift to red faster
            # Lower power = faster shift to red (cooler colors)
            color_power = 0.6
            color_temp = pow(temp_normalized, 1.0 / color_power)
            
            # Use continuous interpolation between colors instead of discrete steps
            color_index_float = color_temp * (len(COLORS) - 1)
            color_index_low = int(color_index_float)
            color_index_high = min(color_index_low + 1, len(COLORS) - 1)
            
            # Linear interpolation between adjacent colors
            t = color_index_float - color_index_low
            color_low = COLORS[color_index_low]
            color_high = COLORS[color_index_high]
            
            # Interpolate RGB values
            r = int(color_low[0] * (1 - t) + color_high[0] * t)
            g = int(color_low[1] * (1 - t) + color_high[1] * t)
            b = int(color_low[2] * (1 - t) + color_high[2] * t)
            
            # Temperature affects alpha - hotter particles are more opaque
            base_alpha = color_low[3] * (1 - t) + color_high[3] * t
            temp_alpha_boost = 0.7 + (temp_normalized * 0.3)  # Range: 0.7-1.0
            alpha = int(base_alpha * temp_alpha_boost)
            
            # Adjust alpha based on depth for layering effect
            depth_alpha = 0.6 + (0.4 * (1.0 - self.depth))  # Front particles more opaque
            final_alpha = int(alpha * depth_alpha)
            
            adjusted_color = (r, g, b, final_alpha)
            
            # Draw particle with dynamic size
            radius = max(1, int(self.current_size))
            pygame.draw.circle(surface, adjusted_color, (int(self.x), int(self.y)), radius)
    
    def reset(self, x, y, temp):
        self.x = x
        self.y = y
        self.temp = temp
        self.vx = random.uniform(-100, 100)
        self.vy = random.uniform(-290, 10)
        self.life = random.uniform(1.5, 3.0)
        self.age = 0
        self.current_size = self.initial_size


def setup():
    # Initialize particles throughout the fire volume
    for _ in range(PARTICLE_COUNT):
        # Choose emission zone (0=core, 1=mid, 2=outer)
        zone = random.choices([0, 1, 2], weights=[0.4, 0.35, 0.25])[0]
        
        if zone == 0:  # Core zone - center of fire volume
            x = FLAME_CENTER + random.uniform(-FLAME_BASE_WIDTH // 4, FLAME_BASE_WIDTH // 4)
            y = HEIGHT - random.randint(0, FIRE_VOLUME_HEIGHT // 2)
            temp = random.uniform(0.7, 1.0)  # Hottest particles, but not all max temp
        elif zone == 1:  # Mid zone
            x = FLAME_CENTER + random.uniform(-FLAME_BASE_WIDTH // 2, FLAME_BASE_WIDTH // 2)
            y = HEIGHT - random.randint(0, FIRE_VOLUME_HEIGHT)
            temp = random.uniform(0.4, 0.8)  # Medium temperature range (more overlap with core)
        else:  # Outer zone
            x = FLAME_CENTER + random.uniform(-FLAME_BASE_WIDTH // 2, FLAME_BASE_WIDTH // 2)
            y = HEIGHT - random.randint(0, FIRE_VOLUME_HEIGHT)
            temp = random.uniform(0.2, 0.6)  # Cooler particles with wider range
        
        particles.append(Particle(x, y, temp, zone))


def update_loop():
    global time_offset
    
    # Update time for turbulence
    time_offset += 1.0 / FPS
    
    # Update particles
    dt = 1.0 / FPS
    for particle in particles[:]:
        if not particle.update(dt):
            
            # Replace with new particle from appropriate zone
            zone = random.choices([0, 1, 2], weights=[0.4, 0.35, 0.25])[0]
            
            if zone == 0:  # Core zone
                x = FLAME_CENTER + random.uniform(-FLAME_BASE_WIDTH // 4, FLAME_BASE_WIDTH // 4)
                y = HEIGHT - random.randint(0, FIRE_VOLUME_HEIGHT // 2)
                temp = random.uniform(0.7, 1.0)
            elif zone == 1:  # Mid zone
                x = FLAME_CENTER + random.uniform(-FLAME_BASE_WIDTH // 2, FLAME_BASE_WIDTH // 2)
                y = HEIGHT - random.randint(0, FIRE_VOLUME_HEIGHT)
                temp = random.uniform(0.6, 0.9)
            else:  # Outer zone
                x = FLAME_CENTER + random.uniform(-FLAME_BASE_WIDTH // 2, FLAME_BASE_WIDTH // 2)
                y = HEIGHT - random.randint(0, FIRE_VOLUME_HEIGHT)
                temp = random.uniform(0.4, 0.8)
            
            particle.reset(x, y, temp)

    # Draw
    screen.fill((0, 0, 0))  # Clear screen
    for particle in particles:
        particle.draw(screen)
    pygame.display.flip()


async def main():
    setup()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
        update_loop()
        await asyncio.sleep(1.0 / FPS)


if __name__ == "__main__":
    asyncio.run(main())