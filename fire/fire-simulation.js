// Fire Simulation - JavaScript Module
// Realistic fire particle system with volumetric emission and turbulence

class FireSimulation {
    constructor(canvasId) {
        // Initialize canvas and context
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        
        // Constants (matching pygame values)
        this.FPS = 60;
        this.WIDTH = 800;
        this.HEIGHT = 600;
        this.PARTICLE_COUNT = 5000;
        this.FLAME_BASE_WIDTH = 200;
        this.FLAME_CENTER = this.WIDTH / 2;
        
        // Volumetric fire parameters
        this.FIRE_VOLUME_HEIGHT = 100;
        this.FIRE_VOLUME_DEPTH = 80;
        this.EMISSION_ZONES = 3;
        
        // Turbulence parameters
        this.TURBULENCE_STRENGTH = 40.0;
        this.TURBULENCE_FREQUENCY = 0.02;
        this.NOISE_SCALE = 0.01;
        
        // Colors for temperature gradient (RGBA) - matching pygame colors exactly
        this.COLORS = [
            [139, 0, 0, 120],     // Dark red (coolest, ~500°C)
            [178, 34, 34, 140],   // Firebrick red
            [220, 20, 60, 150],   // Crimson
            [255, 0, 0, 160],     // Pure red (~600°C)
            [255, 69, 0, 170],    // Red-orange
            [255, 99, 71, 180],   // Tomato
            [255, 140, 0, 190],   // Dark orange
            [255, 165, 0, 200],   // Orange (~800°C)
            [255, 200, 0, 210],   // Golden orange
            [255, 215, 0, 220],   // Gold
            [255, 255, 0, 230],   // Yellow (~1000°C)
            [255, 255, 100, 240], // Light yellow
            [255, 255, 150, 250], // Pale yellow
            [255, 255, 200, 255], // Near-white (~1200°C)
            [255, 255, 255, 255], // White hot (~1500°C+)
        ];
        
        // Global variables
        this.particles = [];
        this.timeOffset = 0.0;
        this.lastTime = 0;
        this.animationId = null;
        
        // Bind methods
        this.updateLoop = this.updateLoop.bind(this);
        
        // Setup keyboard controls
        this.setupControls();
    }
    
    // Utility functions
    random(min, max) {
        return Math.random() * (max - min) + min;
    }
    
    randomInt(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }
    
    randomChoice(choices, weights) {
        const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
        let randomNum = Math.random() * totalWeight;
        
        for (let i = 0; i < choices.length; i++) {
            randomNum -= weights[i];
            if (randomNum <= 0) {
                return choices[i];
            }
        }
        return choices[choices.length - 1];
    }
    
    gaussianRandom(mean, stdDev) {
        // Box-Muller transform for Gaussian random numbers
        const u1 = Math.random();
        const u2 = Math.random();
        const z0 = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
        return z0 * stdDev + mean;
    }
    
    // Noise function for turbulence
    simpleNoise(x, y, time) {
        return (Math.sin(x * this.NOISE_SCALE + time) * 
                Math.cos(y * this.NOISE_SCALE + time * 0.7) * 
                Math.sin((x + y) * this.NOISE_SCALE * 0.5 + time * 1.3));
    }
    
    // Calculate turbulent force
    getTurbulentForce(x, y, time) {
        const noise1 = this.simpleNoise(x, y, time);
        const noise2 = this.simpleNoise(x * 2, y * 2, time * 1.5) * 0.5;
        const noise3 = this.simpleNoise(x * 4, y * 4, time * 2.0) * 0.25;
        
        const combinedNoise = noise1 + noise2 + noise3;
        
        const forceX = combinedNoise * this.TURBULENCE_STRENGTH;
        const forceY = this.simpleNoise(x + 100, y + 100, time) * this.TURBULENCE_STRENGTH * 0.3;
        
        return [forceX, forceY];
    }
    
    // Create a new particle based on emission zone
    createParticle(zone) {
        let x, y, temp;
        
        if (zone === 0) {
            x = this.FLAME_CENTER + this.random(-this.FLAME_BASE_WIDTH / 4, this.FLAME_BASE_WIDTH / 4);
            y = this.HEIGHT - this.randomInt(0, Math.floor(this.FIRE_VOLUME_HEIGHT / 2));
            temp = this.random(0.7, 1.0);
        } else if (zone === 1) {
            x = this.FLAME_CENTER + this.random(-this.FLAME_BASE_WIDTH / 2, this.FLAME_BASE_WIDTH / 2);
            y = this.HEIGHT - this.randomInt(0, this.FIRE_VOLUME_HEIGHT);
            temp = this.random(0.4, 0.8);
        } else {
            x = this.FLAME_CENTER + this.random(-this.FLAME_BASE_WIDTH / 2, this.FLAME_BASE_WIDTH / 2);
            y = this.HEIGHT - this.randomInt(0, this.FIRE_VOLUME_HEIGHT);
            temp = this.random(0.2, 0.6);
        }
        
        return new Particle(this, x, y, temp, zone);
    }
    
    // Initialize particles
    setup() {
        this.particles = [];
        for (let i = 0; i < this.PARTICLE_COUNT; i++) {
            const zone = this.randomChoice([0, 1, 2], [0.4, 0.35, 0.25]);
            this.particles.push(this.createParticle(zone));
        }
    }
    
    // Main update loop
    updateLoop(currentTime) {
        if (this.lastTime === 0) this.lastTime = currentTime;
        const deltaTime = currentTime - this.lastTime;
        
        // Target 60 FPS - only update if enough time has passed
        if (deltaTime < 16) { // ~16.67ms for 60 FPS
            this.animationId = requestAnimationFrame(this.updateLoop);
            return;
        }
        
        this.lastTime = currentTime;
        
        // Use fixed delta time like pygame to maintain consistent speed
        const dt = 1.0 / 60; // Fixed 60 FPS timing
        
        // Update time for turbulence
        this.timeOffset += dt;
        
        // Update particles
        for (let i = this.particles.length - 1; i >= 0; i--) {
            if (!this.particles[i].update(dt)) {
                this.particles.splice(i, 1);
                
                // Replace with new particle
                const zone = this.randomChoice([0, 1, 2], [0.4, 0.35, 0.25]);
                this.particles.push(this.createParticle(zone));
            }
        }
        
        // Clear screen
        this.ctx.fillStyle = 'black';
        this.ctx.fillRect(0, 0, this.WIDTH, this.HEIGHT);
        
        // Draw particles
        for (const particle of this.particles) {
            particle.draw();
        }
        
        this.animationId = requestAnimationFrame(this.updateLoop);
    }
    
    // Setup keyboard controls
    setupControls() {
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                if (document.fullscreenElement) {
                    document.exitFullscreen();
                }
            } else if (event.key === 'f' || event.key === 'F') {
                if (!document.fullscreenElement) {
                    this.canvas.requestFullscreen();
                }
            }
        });
    }
    
    // Start the simulation
    start() {
        this.setup();
        this.animationId = requestAnimationFrame(this.updateLoop);
    }
    
    // Stop the simulation
    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }
}

// Particle class
class Particle {
    constructor(simulation, x, y, temp, emissionZone = 0) {
        this.sim = simulation;
        this.x = x;
        this.y = y;
        this.temp = temp;
        this.emissionZone = emissionZone;
        
        // Initialize velocity based on emission zone
        if (emissionZone === 0) {
            // Core burning zone
            const baseAngle = -Math.PI / 2;
            const angleVariance = Math.PI / 12;
            const angle = this.sim.gaussianRandom(baseAngle, angleVariance);
            
            const baseSpeed = temp * 200.0 + 80.0;
            const speedVariation = this.sim.random(0.8, 1.2);
            const speed = baseSpeed * speedVariation;
            
            this.vx = speed * Math.cos(angle) + this.sim.random(-3.0, 3.0);
            this.vy = speed * Math.sin(angle);
            
        } else if (emissionZone === 1) {
            // Mid-zone
            const baseAngle = Math.random() < 0.5 ? -Math.PI * 5 / 12 : -Math.PI * 7 / 12;
            const angleVariance = Math.PI / 8;
            let angle = this.sim.gaussianRandom(baseAngle, angleVariance);
            angle = Math.max(-3 * Math.PI / 4, Math.min(-Math.PI / 4, angle));
            
            const baseSpeed = temp * 150.0 + 60.0;
            const speedVariation = this.sim.random(0.8, 1.2);
            const speed = baseSpeed * speedVariation;
            
            this.vx = speed * Math.cos(angle) + this.sim.random(-10.0, 10.0);
            this.vy = speed * Math.sin(angle);
            
        } else {
            // Outer zone
            const baseAngle = -Math.PI / 2;
            const angleVariance = Math.PI / 4;
            let angle = this.sim.gaussianRandom(baseAngle, angleVariance);
            
            if (Math.random() < 0.3) {
                if (Math.random() < 0.5) {
                    angle = this.sim.random(-Math.PI / 6, -Math.PI / 3);
                } else {
                    angle = this.sim.random(-2 * Math.PI / 3, -5 * Math.PI / 6);
                }
            } else {
                angle = Math.max(-5 * Math.PI / 6, Math.min(-Math.PI / 6, angle));
            }
            
            const baseSpeed = temp * 100.0 + 50.0;
            const speedVariation = this.sim.random(0.8, 1.2);
            const speed = baseSpeed * speedVariation;
            
            this.vx = speed * Math.cos(angle) + this.sim.random(-15.0, 15.0);
            this.vy = speed * Math.sin(angle);
        }
        
        this.life = this.sim.random(1.5, 3.0);
        this.age = 0;
        this.turbulenceSensitivity = this.sim.random(0.5, 1.5);
        this.initialSize = this.sim.random(4.0, 6.0);
        this.maxSize = this.sim.random(8.0, 12.0);
        this.currentSize = this.initialSize;
        this.depth = Math.random();
    }
    
    update(dt) {
        // Apply turbulent forces
        const [turbX, turbY] = this.sim.getTurbulentForce(this.x, this.y, this.sim.timeOffset);
        this.vx += turbX * dt * this.turbulenceSensitivity;
        this.vy += turbY * dt * this.turbulenceSensitivity;
        
        // Apply velocity damping
        this.vx *= 0.98;
        this.vy *= 0.99;
        
        // Apply buoyancy
        const buoyancyForce = this.temp * 20.0;
        this.vy -= buoyancyForce * dt;
        
        // Apply temperature-based deceleration
        const tempDecayFactor = 0.98 + (this.temp * 0.02);
        this.vx *= tempDecayFactor;
        this.vy *= tempDecayFactor;
        
        // Update position
        this.x += this.vx * dt;
        this.y += this.vy * dt;
        
        // Add swirling motion
        const swirlForce = Math.sin(this.age * 3.0 + this.x * 0.01) * 2.0;
        this.vx += swirlForce * dt;
        
        this.age += dt;
        this.temp -= dt * 0.3;
        
        // Update particle size
        const lifeProgress = this.age / this.life;
        if (lifeProgress < 0.6) {
            const expansionFactor = lifeProgress / 0.8;
            this.currentSize = this.initialSize + (this.maxSize - this.initialSize) * expansionFactor;
        } else {
            const shrinkProgress = (lifeProgress - 0.6) / 0.4;
            const tempFactor = Math.max(0.3, this.temp);
            this.currentSize = this.maxSize * tempFactor;
        }
        
        return this.temp > 0 && this.age < this.life && this.y >= 0 && this.y < this.sim.HEIGHT;
    }
    
    draw() {
        if (this.temp > 0) {
            // Temperature to color mapping
            const tempNormalized = Math.max(0, Math.min(1, this.temp));
            const colorPower = 0.6;
            const colorTemp = Math.pow(tempNormalized, 1.0 / colorPower);
            
            const colorIndexFloat = colorTemp * (this.sim.COLORS.length - 1);
            const colorIndexLow = Math.floor(colorIndexFloat);
            const colorIndexHigh = Math.min(colorIndexLow + 1, this.sim.COLORS.length - 1);
            
            const t = colorIndexFloat - colorIndexLow;
            const colorLow = this.sim.COLORS[colorIndexLow];
            const colorHigh = this.sim.COLORS[colorIndexHigh];
            
            // Interpolate RGB values
            const r = Math.floor(colorLow[0] * (1 - t) + colorHigh[0] * t);
            const g = Math.floor(colorLow[1] * (1 - t) + colorHigh[1] * t);
            const b = Math.floor(colorLow[2] * (1 - t) + colorHigh[2] * t);
            
            // Calculate alpha
            const baseAlpha = colorLow[3] * (1 - t) + colorHigh[3] * t;
            const tempAlphaBoost = 0.7 + (tempNormalized * 0.3);
            const alpha = baseAlpha * tempAlphaBoost;
            
            const depthAlpha = 0.6 + (0.4 * (1.0 - this.depth));
            const finalAlpha = (alpha * depthAlpha) / 255; // Convert to 0-1 range for CSS
            
            // Draw particle
            const radius = Math.max(1, Math.floor(this.currentSize));
            
            this.sim.ctx.globalAlpha = finalAlpha;
            this.sim.ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
            this.sim.ctx.beginPath();
            this.sim.ctx.arc(Math.floor(this.x), Math.floor(this.y), radius, 0, 2 * Math.PI);
            this.sim.ctx.fill();
            this.sim.ctx.globalAlpha = 1.0; // Reset alpha
        }
    }
}

// Initialize the simulation when the page loads
document.addEventListener('DOMContentLoaded', function() {
    const fireSimulation = new FireSimulation('fireCanvas');
    fireSimulation.start();
}); 