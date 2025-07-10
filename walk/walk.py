import pygame
import numpy as np
import math
import time

# Initialize Pygame
pygame.init()
FPS = 60

# Screen dimensions
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Human Walking Simulation")

# Physics constants
GRAVITY = 600.0  # Pixels/second^2 (reduced for more stability)
GROUND_Y = HEIGHT - 100  # Ground level
FRICTION = 0.85  # General friction for motion damping

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
BROWN = (139, 69, 19)
YELLOW = (255, 255, 0)


class Joint:
    """Represents a joint in the skeletal system - massless connection point"""
    def __init__(self, x, y, name="", angle_limits=None):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.name = name
        self.angle_limits = angle_limits  # (min_angle, max_angle) in radians
        
    def update(self, dt):
        # Apply strong damping to prevent runaway acceleration
        self.vx *= 0.95
        self.vy *= 0.95
        
        # Update position
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Ground collision
        if self.y > GROUND_Y:
            self.y = GROUND_Y
            self.vy = 0
            self.vx *= FRICTION  # Ground friction
    
    def apply_force(self, fx, fy):
        # Direct force application - forces will be distributed through bones
        self.vx += fx
        self.vy += fy


class Bone:
    """Represents a bone connecting two joints with distributed mass"""
    def __init__(self, joint1, joint2, mass, length=None, name="", color=WHITE):
        self.joint1 = joint1
        self.joint2 = joint2
        self.rest_length = length if length else self.calculate_distance()
        self.name = name
        # Physical properties
        self.mass = mass
        self.color = color
        
    def calculate_distance(self):
        dx = self.joint2.x - self.joint1.x
        dy = self.joint2.y - self.joint1.y
        return math.sqrt(dx*dx + dy*dy)
    
    def apply_length_constraint(self):
        """Maintain bone length using constraint forces"""
        dx = self.joint2.x - self.joint1.x
        dy = self.joint2.y - self.joint1.y
        current_length = math.sqrt(dx*dx + dy*dy)
        
        if current_length > 0:
            # Calculate the difference from rest length
            difference = current_length - self.rest_length
            percent = difference / current_length / 2.0
            
            # Apply correction
            offset_x = dx * percent
            offset_y = dy * percent
            
            # Move joints to maintain bone length
            self.joint1.x += offset_x
            self.joint1.y += offset_y
            self.joint2.x -= offset_x
            self.joint2.y -= offset_y
    
    def apply_angle_constraint(self, parent_bone=None):
        """Apply joint angle limits if they exist"""
        if self.joint2.angle_limits and parent_bone:
            # Calculate angle between this bone and parent bone
            dx1 = self.joint1.x - parent_bone.joint1.x
            dy1 = self.joint1.y - parent_bone.joint1.y
            dx2 = self.joint2.x - self.joint1.x
            dy2 = self.joint2.y - self.joint1.y
            
            if dx1 != 0 or dy1 != 0:
                parent_angle = math.atan2(dy1, dx1)
                current_angle = math.atan2(dy2, dx2)
                relative_angle = current_angle - parent_angle
                
                # Normalize angle to [-π, π]
                while relative_angle > math.pi:
                    relative_angle -= 2 * math.pi
                while relative_angle < -math.pi:
                    relative_angle += 2 * math.pi

                min_angle, max_angle = self.joint2.angle_limits

                # Apply correction if angle is outside limits
                if relative_angle < min_angle:
                    target_angle = parent_angle + min_angle
                    correction_force = 1.5
                elif relative_angle > max_angle:
                    target_angle = parent_angle + max_angle
                    correction_force = 1.5
                else:
                    return  # Angle is within limits
            
                # Normal angle constraint for non-neck bones
                target_x = self.joint1.x + self.rest_length * math.cos(target_angle)
                target_y = self.joint1.y + self.rest_length * math.sin(target_angle)
                
                force_x = (target_x - self.joint2.x) * correction_force
                force_y = (target_y - self.joint2.y) * correction_force

                self.joint2.apply_force(force_x, force_y)
    
    def draw(self, surface, thickness=3):
        pygame.draw.line(surface, self.color, 
                        (int(self.joint1.x), int(self.joint1.y)),
                        (int(self.joint2.x), int(self.joint2.y)), thickness)


class HumanSkeleton:
    """Complete human skeletal system with proportional dimensions"""
    def __init__(self, x, y, scale=1.0):
        self.scale = scale
        
        # Human body proportions (based on 8-head figure)
        self.head_size = 20 * scale
        self.torso_length = 120 * scale
        self.upper_arm_length = 60 * scale
        self.lower_arm_length = 55 * scale
        self.upper_leg_length = 80 * scale
        self.lower_leg_length = 75 * scale
        self.foot_length = 25 * scale
        
        # Body mass properties - must be set before creating bones
        self.body_mass = 70.0  # kg - average human body mass
        
        # Create joints
        self.joints = {}
        self.create_joints(x, y)
        
        # Create bones with proper mass distribution
        self.bones = []
        self.create_bones()
        
        # Walking state
        self.walking = False
        self.walk_cycle_time = 0.0
        self.walk_speed = 2.0  # Steps per second
        self.step_length = 40 * scale
        
        # Balance and posture maintenance
        self.standing_balance_force = 100.0
        self.posture_force = 50.0
        
    def create_joints(self, center_x, center_y):
        """Create all joints in anatomically correct positions"""
        # Head/neck
        self.joints['head'] = Joint(center_x, center_y - self.torso_length/2 - self.head_size, "head")
        self.joints['neck'] = Joint(center_x, center_y - self.torso_length/2, "neck", angle_limits=(-math.pi/16, math.pi/16))
        
        # Torso
        self.joints['chest'] = Joint(center_x, center_y - self.torso_length/4, "chest", angle_limits=(-math.pi/6, math.pi/6))
        self.joints['waist'] = Joint(center_x, center_y, "waist", angle_limits=(-math.pi/6, math.pi/6))
        self.joints['pelvis'] = Joint(center_x, center_y + self.torso_length/4, "pelvis")
        
        # Left arm - realistic human joint limits
        self.joints['left_shoulder'] = Joint(center_x - 15, center_y - self.torso_length/4, "left_shoulder", angle_limits=(-math.pi/2, math.pi))
        self.joints['left_elbow'] = Joint(center_x - 15, center_y - self.torso_length/4 + self.upper_arm_length, "left_elbow", angle_limits=(-math.pi/6, math.pi*5/6))
        self.joints['left_hand'] = Joint(center_x - 15, center_y - self.torso_length/4 + self.upper_arm_length + self.lower_arm_length, "left_hand", angle_limits=(-math.pi/3, math.pi/3))
        
        # Right arm
        self.joints['right_shoulder'] = Joint(center_x + 15, center_y - self.torso_length/4, "right_shoulder", angle_limits=(-math.pi, math.pi/2))
        self.joints['right_elbow'] = Joint(center_x + 15, center_y - self.torso_length/4 + self.upper_arm_length, "right_elbow", angle_limits=(-math.pi*5/6, math.pi/6))
        self.joints['right_hand'] = Joint(center_x + 15, center_y - self.torso_length/4 + self.upper_arm_length + self.lower_arm_length, "right_hand", angle_limits=(-math.pi/3, math.pi/3))
        
        # Left leg - knees can only bend backward, hips have full range
        self.joints['left_hip'] = Joint(center_x - 10, center_y + self.torso_length/4, "left_hip", angle_limits=(-math.pi/3, math.pi/3))
        self.joints['left_knee'] = Joint(center_x - 10, center_y + self.torso_length/4 + self.upper_leg_length, "left_knee", angle_limits=(-math.pi*2/3, 0))
        self.joints['left_ankle'] = Joint(center_x - 10, center_y + self.torso_length/4 + self.upper_leg_length + self.lower_leg_length, "left_ankle", angle_limits=(-math.pi/3, math.pi/3))
        self.joints['left_foot'] = Joint(center_x - 10 + self.foot_length/2, center_y + self.torso_length/4 + self.upper_leg_length + self.lower_leg_length, "left_foot")
        
        # Right leg
        self.joints['right_hip'] = Joint(center_x + 10, center_y + self.torso_length/4, "right_hip", angle_limits=(-math.pi/3, math.pi/3))
        self.joints['right_knee'] = Joint(center_x + 10, center_y + self.torso_length/4 + self.upper_leg_length, "right_knee", angle_limits=(-math.pi*2/3, 0))
        self.joints['right_ankle'] = Joint(center_x + 10, center_y + self.torso_length/4 + self.upper_leg_length + self.lower_leg_length, "right_ankle", angle_limits=(-math.pi/3, math.pi/3))
        self.joints['right_foot'] = Joint(center_x + 10 + self.foot_length/2, center_y + self.torso_length/4 + self.upper_leg_length + self.lower_leg_length, "right_foot")
    
    def calculate_segment_mass(self, segment_name):
        """Calculate mass based on anatomical data (percentage of total body mass)"""
        # Based on Winter's biomechanics data (1990)
        mass_percentages = {
            # Head and neck
            'head': 0.081,  # 8.1% of body mass
            'neck': 0.014,  # 1.4% of body mass
            
            # Torso
            'upper_spine': 0.158,  # Upper torso ~15.8%
            'mid_spine': 0.102,    # Mid torso ~10.2%
            'lower_spine': 0.097,  # Lower torso ~9.7%
            
            # Arms
            'left_clavicle': 0.028,   # Upper arm ~2.8%
            'right_clavicle': 0.028,
            'left_upper_arm': 0.028,
            'right_upper_arm': 0.028,
            'left_lower_arm': 0.022,  # Forearm + hand ~2.2%
            'right_lower_arm': 0.022,
            
            # Legs
            'left_pelvis': 0.100,      # Thigh ~10%
            'right_pelvis': 0.100,
            'left_upper_leg': 0.100,
            'right_upper_leg': 0.100,
            'left_lower_leg': 0.0465,  # Shank ~4.65%
            'right_lower_leg': 0.0465,
            'left_foot': 0.0145,       # Foot ~1.45%
            'right_foot': 0.0145,
        }
        
        return self.body_mass * mass_percentages.get(segment_name, 0.01)  # Default 1% if unknown

    def create_bones(self):
        """Create all bones connecting joints with realistic mass distribution"""
        # Helper function to create a bone with proper mass properties
        def create_bone(joint1, joint2, name, color=WHITE):
            # Calculate bone length
            dx = joint2.x - joint1.x
            dy = joint2.y - joint1.y
            length = math.sqrt(dx*dx + dy*dy)
            
            # Calculate mass properties using body-wide data
            mass = self.calculate_segment_mass(name)
            
            return Bone(joint1, joint2, mass, length=length, name=name, color=color)
        
        # Spine
        self.bones.append(create_bone(self.joints['head'], self.joints['neck'], "neck"))
        self.bones.append(create_bone(self.joints['neck'], self.joints['chest'], "upper_spine"))
        self.bones.append(create_bone(self.joints['chest'], self.joints['waist'], "mid_spine"))
        self.bones.append(create_bone(self.joints['waist'], self.joints['pelvis'], "lower_spine"))
        
        # Left arm
        self.bones.append(create_bone(self.joints['chest'], self.joints['left_shoulder'], "left_clavicle"))
        self.bones.append(create_bone(self.joints['left_shoulder'], self.joints['left_elbow'], "left_upper_arm"))
        self.bones.append(create_bone(self.joints['left_elbow'], self.joints['left_hand'], "left_lower_arm"))
        
        # Right arm
        self.bones.append(create_bone(self.joints['chest'], self.joints['right_shoulder'], "right_clavicle"))
        self.bones.append(create_bone(self.joints['right_shoulder'], self.joints['right_elbow'], "right_upper_arm"))
        self.bones.append(create_bone(self.joints['right_elbow'], self.joints['right_hand'], "right_lower_arm"))
        
        # Left leg
        self.bones.append(create_bone(self.joints['pelvis'], self.joints['left_hip'], "left_pelvis"))
        self.bones.append(create_bone(self.joints['left_hip'], self.joints['left_knee'], "left_upper_leg"))
        self.bones.append(create_bone(self.joints['left_knee'], self.joints['left_ankle'], "left_lower_leg"))
        self.bones.append(create_bone(self.joints['left_ankle'], self.joints['left_foot'], "left_foot"))
        
        # Right leg
        self.bones.append(create_bone(self.joints['pelvis'], self.joints['right_hip'], "right_pelvis"))
        self.bones.append(create_bone(self.joints['right_hip'], self.joints['right_knee'], "right_upper_leg"))
        self.bones.append(create_bone(self.joints['right_knee'], self.joints['right_ankle'], "right_lower_leg"))
        self.bones.append(create_bone(self.joints['right_ankle'], self.joints['right_foot'], "right_foot"))
    
    def update(self, dt):
        """Update the skeletal system physics"""
        # Update walking cycle
        if self.walking:
            self.walk_cycle_time += dt * self.walk_speed
            self.apply_walking_forces()
        else:
            # Apply standing balance when not walking
            self.maintain_standing_posture()
        
        # Update all joints
        for joint in self.joints.values():
            joint.update(dt)
        
        # Apply gravity to bone centers of mass
        self.apply_gravity_to_bones(dt)
        
        # Apply bone constraints multiple times for stability
        for _ in range(3):  # Multiple iterations for better constraint solving
            for bone in self.bones:
                bone.apply_length_constraint()
            
            # Apply angle constraints for realistic joint limits
            self.apply_angle_constraints()
    
    def apply_walking_forces(self):
        """Apply forces to simulate walking motion"""
        cycle_phase = (self.walk_cycle_time % (2 * math.pi))
        
        # Walking parameters
        leg_swing_amplitude = 30 * self.scale
        arm_swing_amplitude = 20 * self.scale
        vertical_bounce = 5 * self.scale
        
        # Left leg motion (leading by half cycle)
        left_phase = cycle_phase
        left_leg_offset_x = math.sin(left_phase) * leg_swing_amplitude
        left_leg_lift = max(0, math.sin(left_phase) * 15 * self.scale)
        
        # Right leg motion (opposite phase)
        right_phase = cycle_phase + math.pi
        right_leg_offset_x = math.sin(right_phase) * leg_swing_amplitude
        right_leg_lift = max(0, math.sin(right_phase) * 15 * self.scale)
        
        # Apply leg forces
        target_left_foot_x = self.joints['pelvis'].x - 10 + left_leg_offset_x
        target_left_foot_y = GROUND_Y - left_leg_lift
        
        target_right_foot_x = self.joints['pelvis'].x + 10 + right_leg_offset_x
        target_right_foot_y = GROUND_Y - right_leg_lift
        
        # Simple IK-like force application to move feet toward target positions
        foot_force_strength = 10.0  # Reduced from 50.0
        
        # Left foot forces
        dx_left = target_left_foot_x - self.joints['left_foot'].x
        dy_left = target_left_foot_y - self.joints['left_foot'].y
        
        # Limit foot forces
        force_x = max(-100.0, min(100.0, dx_left * foot_force_strength))
        force_y = max(-100.0, min(100.0, dy_left * foot_force_strength))
        self.joints['left_foot'].apply_force(force_x, force_y)
        
        # Right foot forces
        dx_right = target_right_foot_x - self.joints['right_foot'].x
        dy_right = target_right_foot_y - self.joints['right_foot'].y
        
        # Limit foot forces
        force_x = max(-100.0, min(100.0, dx_right * foot_force_strength))
        force_y = max(-100.0, min(100.0, dy_right * foot_force_strength))
        self.joints['right_foot'].apply_force(force_x, force_y)
        
        # Arm swing (opposite to legs) - reduced force
        left_arm_swing = math.sin(cycle_phase + math.pi) * arm_swing_amplitude
        right_arm_swing = math.sin(cycle_phase) * arm_swing_amplitude
        
        # Apply arm forces with limits
        left_force = max(-30.0, min(30.0, left_arm_swing * 2))  # Reduced from 10
        right_force = max(-30.0, min(30.0, right_arm_swing * 2))  # Reduced from 10
        
        self.joints['left_hand'].apply_force(left_force, 0)
        self.joints['right_hand'].apply_force(right_force, 0)
        
        # Body balance and forward motion - reduced
        forward_force = 5.0 * self.scale  # Reduced from 20.0
        self.joints['pelvis'].apply_force(forward_force, 0)
        
        # Vertical bounce - reduced
        bounce = math.sin(cycle_phase * 2) * vertical_bounce
        bounce_force = max(-20.0, min(20.0, bounce * 2))  # Reduced from 10
        self.joints['pelvis'].apply_force(0, bounce_force)
    
    def start_walking(self):
        self.walking = True
        
    def stop_walking(self):
        self.walking = False
    
    def maintain_standing_posture(self):
        """Maintain upright posture when not walking"""
        # Keep feet on ground with gentler force
        for foot_name in ['left_foot', 'right_foot']:
            foot = self.joints[foot_name]
            if foot.y < GROUND_Y:
                force_y = (GROUND_Y - foot.y) * self.standing_balance_force
                # Limit maximum force to prevent overcorrection
                force_y = min(force_y, 100.0)
                foot.apply_force(0, force_y)
        
        # Keep pelvis centered between feet
        left_foot = self.joints['left_foot']
        right_foot = self.joints['right_foot']
        pelvis = self.joints['pelvis']
        
        # Target position for pelvis (centered between feet, appropriate height)
        target_pelvis_x = (left_foot.x + right_foot.x) / 2
        target_pelvis_y = GROUND_Y - self.upper_leg_length - self.lower_leg_length - 20
        
        # Apply corrective forces with limits
        force_x = (target_pelvis_x - pelvis.x) * self.posture_force
        force_y = (target_pelvis_y - pelvis.y) * self.posture_force
        
        # Limit forces to prevent overcorrection
        force_x = max(-300.0, min(300.0, force_x))
        force_y = max(-300.0, min(300.0, force_y))
        
        pelvis.apply_force(force_x, force_y)
        
        # Keep torso upright with gentler forces
        chest = self.joints['chest']
        target_chest_x = pelvis.x
        target_chest_y = pelvis.y - self.torso_length/2
        
        force_x = (target_chest_x - chest.x) * self.posture_force * 0.3  # Reduced multiplier
        force_y = (target_chest_y - chest.y) * self.posture_force * 0.3
        
        # Limit forces
        force_x = max(-50.0, min(50.0, force_x))
        force_y = max(-50.0, min(50.0, force_y))
        
        chest.apply_force(force_x, force_y)
        
        # Keep head above chest with proper settling behavior
        head = self.joints['head']
        target_head_x = chest.x
        target_head_y = chest.y - self.torso_length/2 - self.head_size
        
        # Calculate position errors
        error_x = target_head_x - head.x
        error_y = target_head_y - head.y
        
        # Dead zone - only apply force if error is significant
        dead_zone = 2.0  # pixels
        position_error_magnitude = math.sqrt(error_x*error_x + error_y*error_y)
        
        if position_error_magnitude > dead_zone:
            # Apply proportional force only for significant errors
            force_x = error_x * self.posture_force * 0.1  # Reduced from 0.1
            force_y = error_y * self.posture_force * 0.1
            
            # Limit forces
            force_x = max(-20.0, min(20.0, force_x))
            force_y = max(-20.0, min(20.0, force_y))
            
            head.apply_force(force_x, force_y)
    
    def apply_gravity_to_bones(self, dt):
        """Apply gravity forces to bone centers of mass"""
        for bone in self.bones:
            # Calculate gravitational force
            gravity_force = bone.mass * GRAVITY
            # Apply gravity to both joints equally
            bone.joint1.apply_force(0, gravity_force * 0.5 * dt)
            bone.joint2.apply_force(0, gravity_force * 0.5 * dt)
    
    def apply_angle_constraints(self):
        """Apply angle constraints to all joints with limits"""
        # Create bone hierarchy for angle constraint checking
        bone_hierarchy = {
            'left_upper_arm': ('left_clavicle', 'left_elbow'),
            'left_lower_arm': ('left_upper_arm', 'left_hand'),
            'right_upper_arm': ('right_clavicle', 'right_elbow'),
            'right_lower_arm': ('right_upper_arm', 'right_hand'),
            'left_upper_leg': ('left_pelvis', 'left_knee'),
            'left_lower_leg': ('left_upper_leg', 'left_ankle'),
            'right_upper_leg': ('right_pelvis', 'right_knee'),
            'right_lower_leg': ('right_upper_leg', 'right_ankle'),
            'upper_spine': ('lower_spine', 'neck'),
            'neck': ('upper_spine', 'head')
        }
        
        # Find bones by name
        bone_dict = {bone.name: bone for bone in self.bones}
        
        # Apply angle constraints
        for child_name, (parent_name, _) in bone_hierarchy.items():
            if child_name in bone_dict and parent_name in bone_dict:
                child_bone = bone_dict[child_name]
                parent_bone = bone_dict[parent_name]
                child_bone.apply_angle_constraint(parent_bone)
    
    def draw(self, surface):
        """Draw the complete skeleton"""
        # Draw bones
        for bone in self.bones:
            bone.draw(surface, 3)
        
        # Draw joints
        for joint in self.joints.values():
            color = BLUE
            pygame.draw.circle(surface, color, (int(joint.x), int(joint.y)), 4)
        
        # Draw head
        pygame.draw.circle(surface, YELLOW, 
                         (int(self.joints['head'].x), int(self.joints['head'].y)), 
                         int(self.head_size))

def main():
    clock = pygame.time.Clock()
    
    # Create human skeleton
    human = HumanSkeleton(WIDTH // 2, HEIGHT // 2)
    
    # Display options
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # Delta time in seconds
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if human.walking:
                        human.stop_walking()
                    else:
                        human.start_walking()
                elif event.key == pygame.K_r:
                    # Reset skeleton position
                    human = HumanSkeleton(WIDTH // 2, HEIGHT // 2)
        
        # Update simulation
        human.update(dt)
        
        # Draw everything
        screen.fill(BLACK)
        
        # Draw ground
        pygame.draw.line(screen, GREEN, (0, GROUND_Y), (WIDTH, GROUND_Y), 3)
        
        # Draw skeleton
        human.draw(screen)
        
        # Draw instructions
        font = pygame.font.Font(None, 36)
        instructions = [
            "Press SPACE to start/stop walking",
            "Press R to reset",
            f"Walking: {'ON' if human.walking else 'OFF'}",
            "Status: " + ("Walking" if human.walking else "Standing with balance control"),
        ]
        
        for i, instruction in enumerate(instructions):
            color = WHITE
            if i == 2:  # Walking status line
                color = GREEN if human.walking else RED
            elif i == 3:  # Status line
                color = GREEN if human.walking else YELLOW
            text = font.render(instruction, True, color)
            screen.blit(text, (10, 10 + i * 40))
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()
