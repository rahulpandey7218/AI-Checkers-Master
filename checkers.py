

import pygame
import sys
from pygame import gfxdraw
import random
import time
import threading
import json
import socket
import pickle
from copy import deepcopy
import requests
import os
import uuid
from datetime import datetime
import math

# Firebase configuration - Replace with your actual Firebase config
FIREBASE_API_KEY = "Api key"
FIREBASE_AUTH_URL = "url"
FIREBASE_PROJECT_ID = "ai-checkers-master"  # Replace with your project ID
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"

# Initialize pygame module
pygame.init()

# Game constants
WIDTH, HEIGHT = 900, 800
BOARD_SIZE = 700
ROWS, COLS = 8, 8
SQUARE_SIZE = BOARD_SIZE // COLS
BOARD_OFFSET_X = 50
BOARD_OFFSET_Y = 80
SIDE_PANEL_X = BOARD_OFFSET_X + BOARD_SIZE + 20

# Colors
RED = (255, 50, 50)
WHITE = (240, 240, 240)
BLACK = (30, 30, 30)
DARK_GRAY = (60, 60, 60)
LIGHT_GRAY = (180, 180, 180)
BLUE = (0, 150, 255)
GREEN = (50, 255, 50)
GOLD = (255, 215, 0)
GLOW_BLUE = (0, 200, 255, 100)
PANEL_BG = (40, 40, 50)
DARK_RED = (180, 30, 30)
CREAM = (255, 248, 220)
BROWN = (139, 69, 19)
ORANGE = (255, 165, 0)

# Fonts
FONT_LARGE = pygame.font.SysFont('Arial', 48, bold=True)
FONT_MEDIUM = pygame.font.SysFont('Arial', 32)
FONT_SMALL = pygame.font.SysFont('Arial', 22)
FONT_TINY = pygame.font.SysFont('Arial', 18)

# Set up display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AI CHECKERS MASTER")

class FirestoreAuth:
    def __init__(self):
        self.api_key = FIREBASE_API_KEY
        self.auth_url = FIREBASE_AUTH_URL
        self.firestore_url = FIRESTORE_URL
        self.id_token = None
        self.local_id = None
        self.refresh_token = None
        
    def sign_up(self, email, password):
        """Create a new user account"""
        try:
            url = f"{self.auth_url}:signUp?key={self.api_key}"
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            
            response = requests.post(url, json=payload)
            data = response.json()
            
            if 'error' in data:
                error_message = data['error']['message']
                # Handle specific error messages
                if 'EMAIL_EXISTS' in error_message:
                    return False, "Email already exists. Please try logging in instead."
                elif 'WEAK_PASSWORD' in error_message:
                    return False, "Password is too weak. Please use at least 6 characters."
                elif 'INVALID_EMAIL' in error_message:
                    return False, "Invalid email format."
                else:
                    return False, error_message
            
            self.id_token = data['idToken']
            self.local_id = data['localId']
            self.refresh_token = data['refreshToken']
            
            # Create user profile in Firestore
            self.create_user_profile(data['localId'], email)
            
            return True, "Account created successfully!"
        except requests.exceptions.RequestException:
            return False, "Network error. Please check your internet connection."
        except Exception as e:
            return False, f"Registration failed: {str(e)}"
    
    def sign_in(self, email, password):
        """Sign in with email and password"""
        try:
            url = f"{self.auth_url}:signInWithPassword?key={self.api_key}"
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            
            response = requests.post(url, json=payload)
            data = response.json()
            
            if 'error' in data:
                error_message = data['error']['message']
                # Handle specific error messages
                if 'EMAIL_NOT_FOUND' in error_message:
                    return False, "Email not found. Please register first."
                elif 'INVALID_PASSWORD' in error_message:
                    return False, "Incorrect password."
                elif 'USER_DISABLED' in error_message:
                    return False, "Account has been disabled."
                elif 'INVALID_EMAIL' in error_message:
                    return False, "Invalid email format."
                else:
                    return False, error_message
            
            self.id_token = data['idToken']
            self.local_id = data['localId']
            self.refresh_token = data['refreshToken']
            
            return True, "Login successful!"
        except requests.exceptions.RequestException:
            return False, "Network error. Please check your internet connection."
        except Exception as e:
            return False, f"Login failed: {str(e)}"
    
    def create_user_profile(self, user_id, email):
        """Create a user profile in Firestore"""
        try:
            url = f"{self.firestore_url}/users/{user_id}"
            headers = {
                "Authorization": f"Bearer {self.id_token}",
                "Content-Type": "application/json"
            }
            
            # Firestore document structure
            payload = {
                "fields": {
                    "email": {"stringValue": email},
                    "username": {"stringValue": email.split('@')[0]},
                    "wins": {"integerValue": "0"},
                    "losses": {"integerValue": "0"},
                    "games_played": {"integerValue": "0"},
                    "created_at": {"timestampValue": datetime.now().isoformat() + "Z"}
                }
            }
            
            response = requests.patch(url, json=payload, headers=headers)
            print(f"✅ User profile created in Firestore: {response.status_code}")
            return response.ok
        except Exception as e:
            print(f"❌ Error creating user profile: {e}")
            return False
    
    def get_user_profile(self):
        """Get the current user's profile from Firestore"""
        if not self.local_id or not self.id_token:
            return None
        
        try:
            url = f"{self.firestore_url}/users/{self.local_id}"
            headers = {
                "Authorization": f"Bearer {self.id_token}"
            }
            
            response = requests.get(url, headers=headers)
            if response.ok:
                data = response.json()
                if 'fields' in data:
                    # Convert Firestore format to simple format
                    profile = {}
                    for key, value in data['fields'].items():
                        if 'stringValue' in value:
                            profile[key] = value['stringValue']
                        elif 'integerValue' in value:
                            profile[key] = int(value['integerValue'])
                        elif 'timestampValue' in value:
                            profile[key] = value['timestampValue']
                    return profile
        except Exception as e:
            print(f"❌ Error getting user profile: {e}")
        
        return None
    
    def update_user_stats(self, win=False):
        """Update user statistics after a game"""
        if not self.local_id or not self.id_token:
            return False
        
        try:
            profile = self.get_user_profile()
            if not profile:
                return False
            
            url = f"{self.firestore_url}/users/{self.local_id}"
            headers = {
                "Authorization": f"Bearer {self.id_token}",
                "Content-Type": "application/json"
            }
            
            # Update stats
            new_games_played = profile.get('games_played', 0) + 1
            new_wins = profile.get('wins', 0) + (1 if win else 0)
            new_losses = profile.get('losses', 0) + (0 if win else 1)
            
            payload = {
                "fields": {
                    "email": {"stringValue": profile.get('email', '')},
                    "username": {"stringValue": profile.get('username', '')},
                    "wins": {"integerValue": str(new_wins)},
                    "losses": {"integerValue": str(new_losses)},
                    "games_played": {"integerValue": str(new_games_played)},
                    "created_at": {"timestampValue": profile.get('created_at', datetime.now().isoformat() + "Z")},
                    "last_updated": {"timestampValue": datetime.now().isoformat() + "Z"}
                }
            }
            
            response = requests.patch(url, json=payload, headers=headers)
            print(f"📊 Stats updated: Games={new_games_played}, Wins={new_wins}, Losses={new_losses}")
            return response.ok
        except Exception as e:
            print(f"❌ Error updating stats: {e}")
            return False

class AnimatedPiece:
    """Animated checker piece for decorative purposes"""
    def __init__(self, x, y, color, speed=1):
        self.x = x
        self.y = y
        self.original_x = x
        self.original_y = y
        self.color = color
        self.speed = speed
        self.angle = random.uniform(0, 2 * math.pi)
        self.radius = random.uniform(15, 25)
        self.float_offset = 0
        self.king = random.choice([True, False])
        
    def update(self):
        """Update animation"""
        self.angle += 0.02 * self.speed
        self.float_offset = math.sin(self.angle) * 3
        
    def draw(self, win):
        """Draw animated piece"""
        # Draw shadow
        shadow_x = int(self.x + 2)
        shadow_y = int(self.y + self.float_offset + 2)
        pygame.draw.circle(win, (0, 0, 0, 50), (shadow_x, shadow_y), int(self.radius))
        
        # Draw piece
        piece_x = int(self.x)
        piece_y = int(self.y + self.float_offset)
        
        # Gradient effect
        for i in range(5, 0, -1):
            shade = 20 * i
            if self.color == RED:
                draw_color = (min(255, self.color[0] + shade), 
                             max(0, self.color[1] - shade), 
                             max(0, self.color[2] - shade))
            else:
                draw_color = (min(255, self.color[0] + shade), 
                             min(255, self.color[1] + shade), 
                             min(255, self.color[2] + shade))
            
            pygame.draw.circle(win, draw_color, (piece_x, piece_y), int(self.radius - (5 - i)))
        
        # Draw outline
        pygame.draw.circle(win, BLACK, (piece_x, piece_y), int(self.radius), 2)
        
        # Draw king crown if applicable
        if self.king:
            crown_radius = int(self.radius // 2)
            pygame.draw.circle(win, GOLD, (piece_x, piece_y), crown_radius)
            pygame.draw.circle(win, BLACK, (piece_x, piece_y), crown_radius, 1)

class LoginScreen:
    def __init__(self, win):
        self.win = win
        self.email_input = ""
        self.password_input = ""
        self.focus = "email"
        self.error_message = ""
        self.success_message = ""
        self.firebase = FirestoreAuth()
        self.mode = "login"  # login or register
        
        # Animation variables
        self.animated_pieces = []
        self.board_pattern = []
        self.title_pulse = 0
        self.create_background_elements()
        
    def create_background_elements(self):
        """Create animated background elements"""
        # Create checkerboard pattern
        pattern_size = 40
        for row in range(HEIGHT // pattern_size + 1):
            pattern_row = []
            for col in range(WIDTH // pattern_size + 1):
                if (row + col) % 2 == 0:
                    pattern_row.append(CREAM)
                else:
                    pattern_row.append(BROWN)
            self.board_pattern.append(pattern_row)
        
        # Create floating animated pieces
        for _ in range(12):
            x = random.randint(50, WIDTH - 50)
            y = random.randint(50, HEIGHT - 50)
            color = random.choice([RED, WHITE])
            speed = random.uniform(0.5, 1.5)
            self.animated_pieces.append(AnimatedPiece(x, y, color, speed))
    
    def draw_background(self):
        """Draw animated checkerboard background"""
        # Fill with dark background
        self.win.fill((20, 20, 30))
        
        # Draw subtle checkerboard pattern
        pattern_size = 40
        for row in range(len(self.board_pattern)):
            for col in range(len(self.board_pattern[row])):
                color = self.board_pattern[row][col]
                # Make it very subtle
                alpha_color = (color[0] // 8, color[1] // 8, color[2] // 8)
                rect = pygame.Rect(col * pattern_size, row * pattern_size, pattern_size, pattern_size)
                pygame.draw.rect(self.win, alpha_color, rect)
        
        # Draw animated pieces
        for piece in self.animated_pieces:
            piece.update()
            piece.draw(self.win)
        
        # Draw decorative border
        border_width = 5
        pygame.draw.rect(self.win, GOLD, (0, 0, WIDTH, border_width))
        pygame.draw.rect(self.win, GOLD, (0, HEIGHT - border_width, WIDTH, border_width))
        pygame.draw.rect(self.win, GOLD, (0, 0, border_width, HEIGHT))
        pygame.draw.rect(self.win, GOLD, (WIDTH - border_width, 0, border_width, HEIGHT))
        
    def draw(self):
        """Draw login screen with enhanced design"""
        # Draw animated background
        self.draw_background()
        
        # Update title pulse
        self.title_pulse += 0.05
        
        # Draw main title with enhanced effects
        title_glow = (math.sin(self.title_pulse) + 1) / 2
        title_color = (
            int(50 + 150 * title_glow),
            int(100 + 100 * title_glow),
            255
        )
        
        # Draw title shadow
        shadow_text = FONT_LARGE.render("AI CHECKERS MASTER", True, (0, 0, 0))
        shadow_rect = shadow_text.get_rect(center=(WIDTH//2 + 3, 103))
        self.win.blit(shadow_text, shadow_rect)
        
        # Draw main title
        title_text = FONT_LARGE.render("AI CHECKERS MASTER", True, title_color)
        title_rect = title_text.get_rect(center=(WIDTH//2, 100))
        
        # Create enhanced glow effect
        glow_surface = pygame.Surface((title_rect.width + 60, title_rect.height + 30), pygame.SRCALPHA)
        for i in range(10, 0, -1):
            alpha = int(30 * title_glow * (i / 10))
            glow_color = (*title_color, alpha)
            pygame.draw.rect(glow_surface, glow_color, 
                           (30 - i*3, 15 - i*1.5, title_rect.width + i*6, title_rect.height + i*3), 
                           border_radius=15)
        self.win.blit(glow_surface, (title_rect.x - 30, title_rect.y - 15))
        self.win.blit(title_text, title_rect)
        
        # Draw subtitle
        subtitle_text = FONT_MEDIUM.render("🏆 Master the Game of Strategy 🏆", True, GOLD)
        subtitle_rect = subtitle_text.get_rect(center=(WIDTH//2, 150))
        self.win.blit(subtitle_text, subtitle_rect)
        
        # Draw decorative checkers pieces around title
        piece_positions = [
            (WIDTH//2 - 200, 100), (WIDTH//2 + 200, 100),
            (WIDTH//2 - 150, 60), (WIDTH//2 + 150, 60)
        ]
        for i, (x, y) in enumerate(piece_positions):
            color = RED if i % 2 == 0 else WHITE
            # Animated rotation
            offset_x = math.cos(self.title_pulse + i) * 5
            offset_y = math.sin(self.title_pulse + i) * 3
            
            # Draw piece
            piece_x = int(x + offset_x)
            piece_y = int(y + offset_y)
            
            # Shadow
            pygame.draw.circle(self.win, (0, 0, 0, 100), (piece_x + 2, piece_y + 2), 20)
            
            # Piece with gradient
            for j in range(5, 0, -1):
                shade = 15 * j
                if color == RED:
                    draw_color = (min(255, color[0] + shade), 
                                 max(0, color[1] - shade), 
                                 max(0, color[2] - shade))
                else:
                    draw_color = (min(255, color[0] + shade), 
                                 min(255, color[1] + shade), 
                                 min(255, color[2] + shade))
                
                pygame.draw.circle(self.win, draw_color, (piece_x, piece_y), 20 - (5 - j))
            
            pygame.draw.circle(self.win, BLACK, (piece_x, piece_y), 20, 2)
            
            # King crown
            if i < 2:
                pygame.draw.circle(self.win, GOLD, (piece_x, piece_y), 10)
                pygame.draw.circle(self.win, BLACK, (piece_x, piece_y), 10, 1)
        
        # Draw mode toggle with enhanced styling
        mode_text = "Login" if self.mode == "login" else "Register"
        toggle_text = f"Switch to {('Register' if self.mode == 'login' else 'Login')}"
        
        toggle_button = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 180, 200, 35)
        pygame.draw.rect(self.win, (70, 70, 90), toggle_button, border_radius=17)
        pygame.draw.rect(self.win, BLUE, toggle_button, 2, border_radius=17)
        
        mode_toggle_text = FONT_SMALL.render(toggle_text, True, BLUE)
        mode_toggle_rect = mode_toggle_text.get_rect(center=toggle_button.center)
        self.win.blit(mode_toggle_text, mode_toggle_rect)
        
        # Draw enhanced login form
        form_rect = pygame.Rect(WIDTH//2 - 180, HEIGHT//2 - 120, 360, 280)
        
        # Form background with gradient effect
        form_surface = pygame.Surface((form_rect.width, form_rect.height), pygame.SRCALPHA)
        for i in range(form_rect.height):
            alpha = int(200 - (i / form_rect.height) * 50)
            color = (50, 50, 70, alpha)
            pygame.draw.rect(form_surface, color, (0, i, form_rect.width, 1))
        
        self.win.blit(form_surface, form_rect.topleft)
        pygame.draw.rect(self.win, GOLD, form_rect, 3, border_radius=15)
        
        # Form title with icon
        form_title = FONT_MEDIUM.render(f"👤 {mode_text}", True, WHITE)
        form_title_rect = form_title.get_rect(center=(WIDTH//2, form_rect.y + 40))
        self.win.blit(form_title, form_title_rect)
        
        # Email field with enhanced styling
        email_label = FONT_SMALL.render("📧 Email Address:", True, WHITE)
        self.win.blit(email_label, (form_rect.x + 30, form_rect.y + 80))
        
        email_rect = pygame.Rect(form_rect.x + 30, form_rect.y + 110, 300, 45)
        
        # Field background
        field_color = (40, 40, 60) if self.focus != "email" else (60, 60, 80)
        pygame.draw.rect(self.win, field_color, email_rect, border_radius=8)
        
        # Field border
        border_color = BLUE if self.focus == "email" else LIGHT_GRAY
        border_width = 3 if self.focus == "email" else 1
        pygame.draw.rect(self.win, border_color, email_rect, border_width, border_radius=8)
        
        # Email text
        display_email = self.email_input
        if len(display_email) > 30:
            display_email = display_email[:30] + "..."
        
        email_text = FONT_SMALL.render(display_email, True, WHITE)
        self.win.blit(email_text, (email_rect.x + 15, email_rect.y + 12))
        
        # Cursor for email field
        if self.focus == "email":
            cursor_x = email_rect.x + 15 + email_text.get_width()
            cursor_y1 = email_rect.y + 10
            cursor_y2 = email_rect.y + 35
            if int(time.time() * 2) % 2:  # Blinking cursor
                pygame.draw.line(self.win, WHITE, (cursor_x, cursor_y1), (cursor_x, cursor_y2), 2)
        
        # Password field with enhanced styling
        password_label = FONT_SMALL.render("🔒 Password:", True, WHITE)
        self.win.blit(password_label, (form_rect.x + 30, form_rect.y + 170))
        
        password_rect = pygame.Rect(form_rect.x + 30, form_rect.y + 200, 300, 45)
        
        # Field background
        field_color = (40, 40, 60) if self.focus != "password" else (60, 60, 80)
        pygame.draw.rect(self.win, field_color, password_rect, border_radius=8)
        
        # Field border
        border_color = BLUE if self.focus == "password" else LIGHT_GRAY
        border_width = 3 if self.focus == "password" else 1
        pygame.draw.rect(self.win, border_color, password_rect, border_width, border_radius=8)
        
        # Password text (asterisks)
        password_display = "●" * len(self.password_input)
        password_text = FONT_SMALL.render(password_display, True, WHITE)
        self.win.blit(password_text, (password_rect.x + 15, password_rect.y + 12))
        
        # Cursor for password field
        if self.focus == "password":
            cursor_x = password_rect.x + 15 + password_text.get_width()
            cursor_y1 = password_rect.y + 10
            cursor_y2 = password_rect.y + 35
            if int(time.time() * 2) % 2:  # Blinking cursor
                pygame.draw.line(self.win, WHITE, (cursor_x, cursor_y1), (cursor_x, cursor_y2), 2)
        
        # Enhanced Login/Register button
        button_rect = pygame.Rect(form_rect.x + 105, form_rect.y + 260, 150, 50)
        
        # Button gradient
        button_surface = pygame.Surface((button_rect.width, button_rect.height), pygame.SRCALPHA)
        for i in range(button_rect.height):
            ratio = i / button_rect.height
            color = (
                int(BLUE[0] * (1 - ratio * 0.3)),
                int(BLUE[1] * (1 - ratio * 0.3)),
                int(BLUE[2] * (1 - ratio * 0.3))
            )
            pygame.draw.rect(button_surface, color, (0, i, button_rect.width, 1))
        
        self.win.blit(button_surface, button_rect.topleft)
        pygame.draw.rect(self.win, WHITE, button_rect, 2, border_radius=25)
        
        # Button text
        button_text = FONT_SMALL.render(f"🚀 {mode_text}", True, WHITE)
        button_text_rect = button_text.get_rect(center=button_rect.center)
        self.win.blit(button_text, button_text_rect)
        
        # Error message with enhanced styling
        if self.error_message:
            error_y = form_rect.bottom + 20
            
            # Split long error messages into multiple lines
            words = self.error_message.split(' ')
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                if len(test_line) <= 45:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            # Draw error background
            error_height = len(lines) * 25 + 10
            error_bg = pygame.Rect(WIDTH//2 - 200, error_y - 5, 400, error_height)
            pygame.draw.rect(self.win, (100, 20, 20, 200), error_bg, border_radius=10)
            pygame.draw.rect(self.win, RED, error_bg, 2, border_radius=10)
            
            # Draw each line
            for i, line in enumerate(lines):
                error_text = FONT_SMALL.render(f"⚠️ {line}", True, RED)
                error_rect = error_text.get_rect(center=(WIDTH//2, error_y + i * 25))
                self.win.blit(error_text, error_rect)
        
        # Success message with enhanced styling
        if self.success_message:
            success_y = form_rect.bottom + 20
            success_bg = pygame.Rect(WIDTH//2 - 200, success_y - 5, 400, 35)
            pygame.draw.rect(self.win, (20, 100, 20, 200), success_bg, border_radius=10)
            pygame.draw.rect(self.win, GREEN, success_bg, 2, border_radius=10)
            
            success_text = FONT_SMALL.render(f"✅ {self.success_message}", True, GREEN)
            success_rect = success_text.get_rect(center=(WIDTH//2, success_y + 12))
            self.win.blit(success_text, success_rect)
        
        # Firestore indicator with enhanced styling
        firestore_bg = pygame.Rect(5, HEIGHT - 35, 250, 30)
        pygame.draw.rect(self.win, (20, 60, 20, 150), firestore_bg, border_radius=15)
        firestore_text = FONT_TINY.render("💾 Powered by Cloud Firestore", True, (100, 200, 100))
        self.win.blit(firestore_text, (15, HEIGHT - 30))
    
    def handle_event(self, event):
        """Handle user input events"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Check email field click
            email_rect = pygame.Rect(WIDTH//2 - 150, HEIGHT//2 - 10, 300, 45)
            if email_rect.collidepoint(mouse_pos):
                self.focus = "email"
            
            # Check password field click
            password_rect = pygame.Rect(WIDTH//2 - 150, HEIGHT//2 + 80, 300, 45)
            if password_rect.collidepoint(mouse_pos):
                self.focus = "password"
            
            # Check login/register button click
            button_rect = pygame.Rect(WIDTH//2 - 75, HEIGHT//2 + 140, 150, 50)
            if button_rect.collidepoint(mouse_pos):
                return self.attempt_auth()
            
            # Check mode toggle click
            mode_toggle_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 180, 200, 35)
            if mode_toggle_rect.collidepoint(mouse_pos):
                self.mode = "register" if self.mode == "login" else "login"
                self.error_message = ""
                self.success_message = ""
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                # Switch focus between fields
                self.focus = "password" if self.focus == "email" else "email"
            elif event.key == pygame.K_RETURN:
                # Try to login/register on Enter key
                return self.attempt_auth()
            elif event.key == pygame.K_BACKSPACE:
                # Handle backspace
                if self.focus == "email":
                    self.email_input = self.email_input[:-1]
                else:
                    self.password_input = self.password_input[:-1]
            else:
                # Add character to input (filter out non-printable characters)
                if event.unicode.isprintable():
                    if self.focus == "email":
                        self.email_input += event.unicode
                    else:
                        self.password_input += event.unicode
        
        return None
    
    def attempt_auth(self):
        """Verify login credentials or register new user"""
        # Clear previous messages
        self.error_message = ""
        self.success_message = ""
        
        # Validate input
        if not self.email_input.strip() or not self.password_input:
            self.error_message = "Email and password cannot be empty"
            return None
        
        email = self.email_input.strip().lower()
        
        # Basic email validation
        if '@' not in email or '.' not in email.split('@')[-1]:
            self.error_message = "Please enter a valid email address"
            return None
        
        if len(self.password_input) < 6:
            self.error_message = "Password must be at least 6 characters"
            return None
        
        # Attempt authentication
        if self.mode == "login":
            success, message = self.firebase.sign_in(email, self.password_input)
        else:  # register
            success, message = self.firebase.sign_up(email, self.password_input)
        
        if success:
            self.success_message = message
            self.error_message = ""
            # Get username from email (before the @)
            username = email.split('@')[0]
            print(f"🎉 Authentication successful for: {username}")
            return username
        else:
            self.error_message = message
            self.success_message = ""
            return None

class GameMenu:
    def __init__(self, win, username, firebase_auth=None):
        self.win = win
        self.username = username
        self.firebase_auth = firebase_auth
        self.selected_option = 0
        self.options = [
            "Human vs Human",
            "Human vs AI (Easy)",
            "Human vs AI (Medium)",
            "Human vs AI (Hard)",
            "View Statistics",
            "Logout"
        ]
        self.ai_difficulty = None
        self.game_mode = None
        self.show_stats = False
        self.user_stats = None
        
        # Animation variables
        self.menu_pulse = 0
        self.floating_pieces = []
        self.create_menu_decorations()
    
    def create_menu_decorations(self):
        """Create decorative elements for menu"""
        # Create floating pieces around the menu
        for _ in range(8):
            x = random.randint(50, WIDTH - 50)
            y = random.randint(200, HEIGHT - 100)
            color = random.choice([RED, WHITE])
            speed = random.uniform(0.3, 0.8)
            self.floating_pieces.append(AnimatedPiece(x, y, color, speed))
    
    def draw_background(self):
        """Draw animated background for menu"""
        # Gradient background
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            color = (
                int(20 + ratio * 20),
                int(20 + ratio * 30),
                int(40 + ratio * 20)
            )
            pygame.draw.line(self.win, color, (0, y), (WIDTH, y))
        
        # Draw floating pieces
        for piece in self.floating_pieces:
            piece.update()
            piece.draw(self.win)
        
        # Draw decorative checkerboard corners
        corner_size = 60
        for corner_x, corner_y in [(0, 0), (WIDTH - corner_size, 0), (0, HEIGHT - corner_size), (WIDTH - corner_size, HEIGHT - corner_size)]:
            for row in range(corner_size // 10):
                for col in range(corner_size // 10):
                    if (row + col) % 2 == 0:
                        color = BROWN
                    else:
                        color = CREAM
                    
                    # Make it subtle
                    alpha_color = (color[0] // 4, color[1] // 4, color[2] // 4)
                    rect = pygame.Rect(corner_x + col * 10, corner_y + row * 10, 10, 10)
                    pygame.draw.rect(self.win, alpha_color, rect)
    
    def draw(self):
        """Draw the game menu with enhanced design"""
        # Draw animated background
        self.draw_background()
        
        # Update animation
        self.menu_pulse += 0.03
        
        if self.show_stats:
            self.draw_stats()
        else:
            self.draw_menu()
    
    def draw_menu(self):
        """Draw the main menu with enhanced styling"""
        # Draw enhanced title
        title_glow = (math.sin(self.menu_pulse) + 1) / 2
        title_color = (
            int(50 + 150 * title_glow),
            int(100 + 100 * title_glow),
            255
        )
        
        # Title shadow
        shadow_text = FONT_LARGE.render("AI CHECKERS MASTER", True, (0, 0, 0))
        shadow_rect = shadow_text.get_rect(center=(WIDTH//2 + 3, 103))
        self.win.blit(shadow_text, shadow_rect)
        
        # Main title
        title_text = FONT_LARGE.render("AI CHECKERS MASTER", True, title_color)
        title_rect = title_text.get_rect(center=(WIDTH//2, 100))
        
        # Enhanced glow effect
        glow_surface = pygame.Surface((title_rect.width + 60, title_rect.height + 30), pygame.SRCALPHA)
        for i in range(8, 0, -1):
            alpha = int(40 * title_glow * (i / 8))
            glow_color = (*title_color, alpha)
            pygame.draw.rect(glow_surface, glow_color, 
                           (30 - i*4, 15 - i*2, title_rect.width + i*8, title_rect.height + i*4), 
                           border_radius=20)
        self.win.blit(glow_surface, (title_rect.x - 30, title_rect.y - 15))
        self.win.blit(title_text, title_rect)
        
        # Draw welcome message with crown
        welcome_text = FONT_MEDIUM.render(f"👑 Welcome, {self.username}! 👑", True, GOLD)
        welcome_rect = welcome_text.get_rect(center=(WIDTH//2, 180))
        
        # Welcome message background
        welcome_bg = pygame.Rect(welcome_rect.x - 20, welcome_rect.y - 10, welcome_rect.width + 40, welcome_rect.height + 20)
        pygame.draw.rect(self.win, (50, 50, 70, 150), welcome_bg, border_radius=15)
        pygame.draw.rect(self.win, GOLD, welcome_bg, 2, border_radius=15)
        
        self.win.blit(welcome_text, welcome_rect)
        
        # Draw enhanced menu options
        menu_rect = pygame.Rect(WIDTH//2 - 200, 230, 400, 420)
        
        # Menu background with gradient
        menu_surface = pygame.Surface((menu_rect.width, menu_rect.height), pygame.SRCALPHA)
        for i in range(menu_rect.height):
            alpha = int(180 - (i / menu_rect.height) * 60)
            color = (40, 40, 60, alpha)
            pygame.draw.rect(menu_surface, color, (0, i, menu_rect.width, 1))
        
        self.win.blit(menu_surface, menu_rect.topleft)
        pygame.draw.rect(self.win, GOLD, menu_rect, 3, border_radius=20)
        
        # Menu title
        menu_title = FONT_MEDIUM.render("🎮 Game Modes", True, WHITE)
        menu_title_rect = menu_title.get_rect(center=(WIDTH//2, menu_rect.y + 30))
        self.win.blit(menu_title, menu_title_rect)
        
        # Draw menu options with enhanced styling
        for i, option in enumerate(self.options):
            option_rect = pygame.Rect(menu_rect.x + 30, menu_rect.y + 70 + i * 55, 340, 45)
            
            # Option background and highlighting
            if i == self.selected_option:
                # Animated selection
                pulse = (math.sin(self.menu_pulse * 3) + 1) / 2
                glow_alpha = int(100 + pulse * 50)
                
                # Selection glow
                glow_rect = pygame.Rect(option_rect.x - 5, option_rect.y - 5, option_rect.width + 10, option_rect.height + 10)
                pygame.draw.rect(self.win, (*BLUE, glow_alpha), glow_rect, border_radius=25)
                
                # Selection background
                pygame.draw.rect(self.win, (70, 70, 100), option_rect, border_radius=22)
                pygame.draw.rect(self.win, BLUE, option_rect, 3, border_radius=22)
                text_color = WHITE
            else:
                # Normal background
                pygame.draw.rect(self.win, (50, 50, 70), option_rect, border_radius=22)
                pygame.draw.rect(self.win, LIGHT_GRAY, option_rect, 1, border_radius=22)
                text_color = LIGHT_GRAY
            
            # Option icons and text
            icons = ["👥", "🤖", "🧠", "🔥", "📊", "🚪"]
            option_text = f"{icons[i]} {option}"
            
            text_surface = FONT_SMALL.render(option_text, True, text_color)
            text_rect = text_surface.get_rect(center=option_rect.center)
            self.win.blit(text_surface, text_rect)
            
            # Add difficulty indicators for AI modes
            if "AI" in option:
                difficulty_colors = {"Easy": GREEN, "Medium": ORANGE, "Hard": RED}
                for diff, color in difficulty_colors.items():
                    if diff in option:
                        indicator_rect = pygame.Rect(option_rect.right - 40, option_rect.y + 5, 30, 35)
                        pygame.draw.rect(self.win, color, indicator_rect, border_radius=15)
                        break
        
        # Draw decorative elements
        self.draw_menu_decorations()
        
        # Firestore indicator
        firestore_bg = pygame.Rect(5, HEIGHT - 35, 280, 30)
        pygame.draw.rect(self.win, (20, 60, 20, 150), firestore_bg, border_radius=15)
        firestore_text = FONT_TINY.render("💾 Your progress saved in Cloud Firestore", True, (100, 200, 100))
        self.win.blit(firestore_text, (15, HEIGHT - 30))
    
    def draw_menu_decorations(self):
        """Draw decorative elements around the menu"""
        # Draw animated checker pieces in corners
        corner_pieces = [
            (100, 300, RED), (WIDTH - 100, 300, WHITE),
            (100, 500, WHITE), (WIDTH - 100, 500, RED)
        ]
        
        for x, y, color in corner_pieces:
            # Animated floating effect
            offset_x = math.cos(self.menu_pulse + x/100) * 8
            offset_y = math.sin(self.menu_pulse + y/100) * 5
            
            piece_x = int(x + offset_x)
            piece_y = int(y + offset_y)
            
            # Shadow
            pygame.draw.circle(self.win, (0, 0, 0, 80), (piece_x + 3, piece_y + 3), 25)
            
            # Piece with gradient
            for j in range(6, 0, -1):
                shade = 20 * j
                if color == RED:
                    draw_color = (min(255, color[0] + shade), 
                                 max(0, color[1] - shade), 
                                 max(0, color[2] - shade))
                else:
                    draw_color = (min(255, color[0] + shade), 
                                 min(255, color[1] + shade), 
                                 min(255, color[2] + shade))
                
                pygame.draw.circle(self.win, draw_color, (piece_x, piece_y), 25 - (6 - j))
            
            pygame.draw.circle(self.win, BLACK, (piece_x, piece_y), 25, 3)
            
            # King crown
            pygame.draw.circle(self.win, GOLD, (piece_x, piece_y), 12)
            pygame.draw.circle(self.win, BLACK, (piece_x, piece_y), 12, 2)
    
    def draw_stats(self):
        """Draw user statistics with enhanced styling"""
        # Back button with enhanced styling
        back_rect = pygame.Rect(50, 150, 120, 50)
        pygame.draw.rect(self.win, (70, 70, 90), back_rect, border_radius=25)
        pygame.draw.rect(self.win, BLUE, back_rect, 3, border_radius=25)
        
        back_text = FONT_SMALL.render("← Back", True, WHITE)
        back_text_rect = back_text.get_rect(center=back_rect.center)
        self.win.blit(back_text, back_text_rect)
        
        # Stats panel with enhanced design
        stats_rect = pygame.Rect(WIDTH//2 - 250, 200, 500, 400)
        
        # Stats background with gradient
        stats_surface = pygame.Surface((stats_rect.width, stats_rect.height), pygame.SRCALPHA)
        for i in range(stats_rect.height):
            alpha = int(200 - (i / stats_rect.height) * 50)
            color = (40, 40, 70, alpha)
            pygame.draw.rect(stats_surface, color, (0, i, stats_rect.width, 1))
        
        self.win.blit(stats_surface, stats_rect.topleft)
        pygame.draw.rect(self.win, GOLD, stats_rect, 4, border_radius=20)
        
        # Stats title
        stats_title = FONT_MEDIUM.render("📊 Your Game Statistics", True, WHITE)
        stats_title_rect = stats_title.get_rect(center=(WIDTH//2, 240))
        self.win.blit(stats_title, stats_title_rect)
        
        if self.user_stats:
            y_offset = 300
            games = self.user_stats.get('games_played', 0)
            wins = self.user_stats.get('wins', 0)
            losses = self.user_stats.get('losses', 0)
            win_rate = (wins / games * 100) if games > 0 else 0
            
            stats_items = [
                ("🎮", "Games Played", str(games), BLUE),
                ("🏆", "Victories", str(wins), GREEN),
                ("💔", "Defeats", str(losses), RED),
                ("📈", "Win Rate", f"{win_rate:.1f}%", GOLD)
            ]
            
            for icon, label, value, color in stats_items:
                # Stat item background
                item_rect = pygame.Rect(stats_rect.x + 40, y_offset - 10, 420, 50)
                pygame.draw.rect(self.win, (60, 60, 80, 150), item_rect, border_radius=15)
                pygame.draw.rect(self.win, color, item_rect, 2, border_radius=15)
                
                # Icon
                icon_text = FONT_MEDIUM.render(icon, True, color)
                self.win.blit(icon_text, (item_rect.x + 20, item_rect.y + 10))
                
                # Label
                label_text = FONT_SMALL.render(label, True, WHITE)
                self.win.blit(label_text, (item_rect.x + 70, item_rect.y + 15))
                
                # Value
                value_text = FONT_SMALL.render(value, True, color)
                value_rect = value_text.get_rect(right=item_rect.right - 20, centery=item_rect.centery)
                self.win.blit(value_text, value_rect)
                
                y_offset += 70
            
            # Achievement badges
            if games >= 10:
                badge_text = FONT_SMALL.render("🎖️ Veteran Player", True, GOLD)
                badge_rect = badge_text.get_rect(center=(WIDTH//2, y_offset + 20))
                self.win.blit(badge_text, badge_rect)
            
            if win_rate >= 70:
                master_text = FONT_SMALL.render("👑 Checkers Master", True, GOLD)
                master_rect = master_text.get_rect(center=(WIDTH//2, y_offset + 50))
                self.win.blit(master_text, master_rect)
                
        else:
            # Loading animation
            loading_dots = "." * (int(time.time() * 2) % 4)
            loading_text = FONT_SMALL.render(f"Loading your stats{loading_dots}", True, LIGHT_GRAY)
            loading_rect = loading_text.get_rect(center=(WIDTH//2, 400))
            self.win.blit(loading_text, loading_rect)
    
    def handle_event(self, event):
        """Handle user input events"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            if self.show_stats:
                # Back button
                back_rect = pygame.Rect(50, 150, 120, 50)
                if back_rect.collidepoint(mouse_pos):
                    self.show_stats = False
                    return None
            else:
                # Check if any menu option was clicked
                menu_rect = pygame.Rect(WIDTH//2 - 200, 230, 400, 420)
                for i, option in enumerate(self.options):
                    option_rect = pygame.Rect(menu_rect.x + 30, menu_rect.y + 70 + i * 55, 340, 45)
                    if option_rect.collidepoint(mouse_pos):
                        return self.select_option(i)
        
        elif event.type == pygame.KEYDOWN:
            if not self.show_stats:
                if event.key == pygame.K_UP:
                    self.selected_option = (self.selected_option - 1) % len(self.options)
                elif event.key == pygame.K_DOWN:
                    self.selected_option = (self.selected_option + 1) % len(self.options)
                elif event.key == pygame.K_RETURN:
                    return self.select_option(self.selected_option)
            else:
                if event.key == pygame.K_ESCAPE:
                    self.show_stats = False
        
        return None
    
    def select_option(self, option_index):
        """Handle menu option selection"""
        selected = self.options[option_index]
        
        if selected == "Human vs Human":
            self.game_mode = "human_vs_human"
            return "start_game"
        elif selected.startswith("Human vs AI"):
            self.game_mode = "human_vs_ai"
            if "Easy" in selected:
                self.ai_difficulty = "easy"
            elif "Medium" in selected:
                self.ai_difficulty = "medium"
            else:
                self.ai_difficulty = "hard"
            return "start_game"
        elif selected == "View Statistics":
            self.show_stats = True
            # Load user stats
            if self.firebase_auth:
                self.user_stats = self.firebase_auth.get_user_profile()
            return None
        elif selected == "Logout":
            return "logout"
        
        return None

# [Rest of the classes remain the same - Piece, Board, Game, etc.]
# I'll include the essential classes here for completeness

class Piece:
    PADDING = 15
    OUTLINE = 3
    GLOW_SIZE = 20
    
    def __init__(self, row, col, color):
        self.row = row
        self.col = col
        self.color = color
        self.king = False
        self.x = 0
        self.y = 0
        self.calc_pos()
        self.selected = False

    def calc_pos(self):
        """Calculate the piece's position on the board"""
        self.x = BOARD_OFFSET_X + SQUARE_SIZE * self.col + SQUARE_SIZE // 2
        self.y = BOARD_OFFSET_Y + SQUARE_SIZE * self.row + SQUARE_SIZE // 2

    def make_king(self):
        """Promote the piece to a king"""
        self.king = True

    def draw(self, win):
        """Draw the piece on the board with enhanced visuals"""
        radius = SQUARE_SIZE // 2 - self.PADDING
        
        # Draw glow effect if selected
        if self.selected:
            glow_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, GLOW_BLUE, 
                             (SQUARE_SIZE//2, SQUARE_SIZE//2), 
                             radius + self.GLOW_SIZE)
            win.blit(glow_surface, (self.x - SQUARE_SIZE//2, self.y - SQUARE_SIZE//2))
        
        # Draw piece with gradient effect
        for i in range(5, 0, -1):
            shade = 20 * i
            if self.color == RED:
                draw_color = (min(255, self.color[0] + shade), 
                             max(0, self.color[1] - shade), 
                             max(0, self.color[2] - shade))
            else:
                draw_color = (min(255, self.color[0] + shade), 
                             min(255, self.color[1] + shade), 
                             min(255, self.color[2] + shade))
            
            pygame.draw.circle(win, draw_color, (self.x, self.y), radius - (5 - i))
        
        # Draw outline
        pygame.draw.circle(win, BLACK, (self.x, self.y), radius + 1, 1)
        
        # Draw king crown
        if self.king:
            crown_radius = radius // 2
            pygame.draw.circle(win, GOLD, (self.x, self.y), crown_radius)
            pygame.draw.circle(win, BLACK, (self.x, self.y), crown_radius, 1)

    def move(self, row, col):
        """Move the piece to a new position"""
        self.row = row
        self.col = col
        self.calc_pos()
        
    def __repr__(self):
        return f"Piece({self.row}, {self.col}, {self.color}, king={self.king})"
        
    def copy(self):
        """Create a deep copy of the piece"""
        copy_piece = Piece(self.row, self.col, self.color)
        copy_piece.king = self.king
        return copy_piece

class Board:
    def __init__(self):
        self.board = []
        self.red_left = self.white_left = 12
        self.red_kings = self.white_kings = 0
        self.create_board()

    def draw_squares(self, win):
        """Draw the checkerboard pattern with enhanced visuals"""
        # Draw board background
        pygame.draw.rect(win, DARK_GRAY, 
                       (BOARD_OFFSET_X - 10, BOARD_OFFSET_Y - 10, 
                        BOARD_SIZE + 20, BOARD_SIZE + 20), 
                        border_radius=5)
        
        for row in range(ROWS):
            for col in range(COLS):
                if (row + col) % 2 == 0:
                    color = LIGHT_GRAY
                else:
                    color = BLACK
                
                # Draw square
                pygame.draw.rect(win, color, 
                               (BOARD_OFFSET_X + col * SQUARE_SIZE, 
                                BOARD_OFFSET_Y + row * SQUARE_SIZE, 
                                SQUARE_SIZE, SQUARE_SIZE))

    def create_board(self):
        """Initialize the board with pieces in starting positions"""
        for row in range(ROWS):
            self.board.append([])
            for col in range(COLS):
                if (row + col) % 2 == 1:
                    if row < 3:
                        self.board[row].append(Piece(row, col, WHITE))
                    elif row > 4:
                        self.board[row].append(Piece(row, col, RED))
                    else:
                        self.board[row].append(0)
                else:
                    self.board[row].append(0)

    def draw(self, win):
        """Draw the entire board"""
        self.draw_squares(win)
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.board[row][col]
                if piece != 0:
                    piece.draw(win)

    def move(self, piece, row, col):
        """Move a piece and handle king promotion"""
        if piece != 0 and hasattr(piece, 'row') and hasattr(piece, 'col'):
            self.board[piece.row][piece.col], self.board[row][col] = self.board[row][col], self.board[piece.row][piece.col]
            piece.move(row, col)
            
            # Check for king promotion
            if row == 0 and piece.color == RED:
                if not piece.king:
                    piece.make_king()
                    self.red_kings += 1
            elif row == ROWS - 1 and piece.color == WHITE:
                if not piece.king:
                    piece.make_king()
                    self.white_kings += 1

    def get_piece(self, row, col):
        """Get piece at specific position"""
        if 0 <= row < ROWS and 0 <= col < COLS:
            return self.board[row][col]
        return None

    def remove(self, pieces):
        """Remove captured pieces from the board"""
        for piece in pieces:
            if piece != 0 and hasattr(piece, 'row') and hasattr(piece, 'col'):
                self.board[piece.row][piece.col] = 0
                if piece.color == RED:
                    self.red_left -= 1
                else:
                    self.white_left -= 1
                    
    def copy(self):
        """Create a deep copy of the board"""
        new_board = Board()
        new_board.board = []
        new_board.red_left = self.red_left
        new_board.white_left = self.white_left
        new_board.red_kings = self.red_kings
        new_board.white_kings = self.white_kings
        
        for row in range(ROWS):
            new_board.board.append([])
            for col in range(COLS):
                piece = self.board[row][col]
                if piece != 0:
                    new_board.board[row].append(piece.copy())
                else:
                    new_board.board[row].append(0)
                    
        return new_board
        
    def get_all_pieces(self, color):
        """Get all pieces of a specific color"""
        pieces = []
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.board[row][col]
                if piece != 0 and piece.color == color:
                    pieces.append(piece)
        return pieces
        
    def evaluate(self):
        """Evaluate the board state (positive is good for RED, negative for WHITE)"""
        # Basic evaluation: piece count and king count
        piece_value = (self.red_left - self.white_left)
        king_value = (self.red_kings - self.white_kings) * 0.5
        
        # Advanced evaluation: position value
        position_value = 0
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.board[row][col]
                if piece != 0:
                    # Pieces closer to promotion are more valuable
                    if piece.color == RED:
                        position_value += (ROWS - 1 - row) * 0.05
                    else:
                        position_value -= row * 0.05
                    
                    # Center control is valuable
                    center_distance = abs(col - 3.5) + abs(row - 3.5)
                    if piece.color == RED:
                        position_value += (7 - center_distance) * 0.02
                    else:
                        position_value -= (7 - center_distance) * 0.02
        
        return piece_value + king_value + position_value

class Game:
    def __init__(self, win, username=None, game_mode="human_vs_human", ai_difficulty=None, firebase_auth=None):
        self.win = win
        self.username = username
        self.board = Board()
        self.turn = RED
        self.selected = None
        self.valid_moves = {}
        self.game_over = False
        self.winner = None
        self.turn_indicator_time = 0
        self.clock = pygame.time.Clock()
        self.title_glow = 0
        self.title_glow_dir = 1
        
        # Firebase integration
        self.firebase_auth = firebase_auth
        
        # Game mode and AI settings
        self.game_mode = game_mode
        self.ai_difficulty = ai_difficulty
        self.ai_color = WHITE  # AI plays as white by default
        self.ai_thinking = False
        
        # Undo/Redo functionality
        self.move_history = []
        self.future_moves = []
        
        # Monte Carlo simulation variables
        self.monte_carlo_running = False
        self.monte_carlo_results = {"RED": 0, "WHITE": 0, "DRAW": 0}
        self.monte_carlo_total = 0
        self.monte_carlo_thread = None
        self.auto_monte_carlo = True
        self.simulation_speed = 300
        
        # UI elements
        self.show_buttons = True
        self.buttons = {
            "undo": pygame.Rect(BOARD_OFFSET_X, HEIGHT - 100, 100, 40),
            "redo": pygame.Rect(BOARD_OFFSET_X + 110, HEIGHT - 100, 100, 40),
            "menu": pygame.Rect(WIDTH - 150, HEIGHT - 100, 100, 40)
        }

    def update(self):
        """Update the game display"""
        self.clock.tick(60)
        self.draw_background()
        self.board.draw(self.win)
        self.draw_valid_moves()
        self.draw_side_panel()
        self.draw_ui()
        
        # Make AI move if it's AI's turn
        if (self.game_mode == "human_vs_ai" and 
            ((self.turn == WHITE and self.ai_color == WHITE) or 
             (self.turn == RED and self.ai_color == RED)) and
            not self.game_over and not self.ai_thinking):
            self.ai_thinking = True
            self.ai_move()
            self.ai_thinking = False
        
        pygame.display.update()

    def draw_background(self):
        """Draw animated background elements"""
        # Fill background
        self.win.fill((30, 30, 40))
        
        # Animate title glow
        self.title_glow += 0.05 * self.title_glow_dir
        if self.title_glow > 1 or self.title_glow < 0:
            self.title_glow_dir *= -1
        
        # Draw glowing title
        title_text = FONT_LARGE.render("AI CHECKERS MASTER", True, 
                                     (0, 200 + int(55 * self.title_glow), 
                                     255))
        title_rect = title_text.get_rect(center=(WIDTH//2, 40))
        
        # Create glow effect
        glow_surface = pygame.Surface((title_rect.width + 40, title_rect.height + 20), pygame.SRCALPHA)
        pygame.draw.rect(glow_surface, (0, 100, 150, 30), 
                         (0, 0, title_rect.width + 40, title_rect.height + 20), 
                         border_radius=10)
        self.win.blit(glow_surface, (title_rect.x - 20, title_rect.y - 10))
        self.win.blit(title_text, title_rect)

    def draw_side_panel(self):
        """Draw side panel with Monte Carlo results"""
        # Draw panel background
        panel_rect = pygame.Rect(SIDE_PANEL_X, BOARD_OFFSET_Y, WIDTH - SIDE_PANEL_X - 20, BOARD_SIZE)
        pygame.draw.rect(self.win, PANEL_BG, panel_rect, border_radius=10)
        
        # Draw panel title
        panel_title = FONT_MEDIUM.render("Win Probability", True, WHITE)
        self.win.blit(panel_title, (SIDE_PANEL_X + 10, BOARD_OFFSET_Y + 20))
        
        # Draw separator line
        pygame.draw.line(self.win, LIGHT_GRAY, 
                       (SIDE_PANEL_X + 10, BOARD_OFFSET_Y + 60), 
                       (WIDTH - 30, BOARD_OFFSET_Y + 60), 2)
        
        # Draw Monte Carlo results
        y_offset = BOARD_OFFSET_Y + 80
        
        if self.monte_carlo_total > 0:
            # Calculate percentages
            red_pct = (self.monte_carlo_results["RED"] / self.monte_carlo_total) * 100
            white_pct = (self.monte_carlo_results["WHITE"] / self.monte_carlo_total) * 100
            draw_pct = (self.monte_carlo_results["DRAW"] / self.monte_carlo_total) * 100
            
            # Draw bars
            self.draw_probability_bar("RED", red_pct, y_offset)
            self.draw_probability_bar("WHITE", white_pct, y_offset + 80)
            self.draw_probability_bar("DRAW", draw_pct, y_offset + 160)
            
            # Show total simulations
            total_text = FONT_SMALL.render(f"Simulations: {self.monte_carlo_total}", True, LIGHT_GRAY)
            self.win.blit(total_text, (SIDE_PANEL_X + 10, y_offset + 240))
            
            # Show loading animation if simulation is running
            if self.monte_carlo_running:
                dots = "." * (int(time.time() * 2) % 4)
                running_text = FONT_SMALL.render(f"Simulating{dots}", True, GREEN)
                self.win.blit(running_text, (SIDE_PANEL_X + 10, y_offset + 270))
        else:
            # Show waiting message
            if self.monte_carlo_running:
                dots = "." * (int(time.time() * 2) % 4)
                waiting_text = FONT_MEDIUM.render(f"Calculating{dots}", True, BLUE)
                self.win.blit(waiting_text, (SIDE_PANEL_X + 20, y_offset + 100))
            else:
                waiting_text = FONT_MEDIUM.render("Waiting for move", True, LIGHT_GRAY)
                self.win.blit(waiting_text, (SIDE_PANEL_X + 10, y_offset + 100))
        
        # Draw game mode info
        mode_text = ""
        if self.game_mode == "human_vs_human":
            mode_text = "Mode: Human vs Human"
        elif self.game_mode == "human_vs_ai":
            mode_text = f"Mode: Human vs AI ({self.ai_difficulty.capitalize()})"
        
        mode_render = FONT_SMALL.render(mode_text, True, LIGHT_GRAY)
        self.win.blit(mode_render, (SIDE_PANEL_X + 10, y_offset + 300))
        
        # Draw player info if available
        if self.username:
            player_text = FONT_SMALL.render(f"Player: {self.username}", True, LIGHT_GRAY)
            self.win.blit(player_text, (SIDE_PANEL_X + 10, y_offset + 330))
        
        # Firestore indicator
        firestore_text = FONT_TINY.render("💾 Firestore", True, (100, 200, 100))
        self.win.blit(firestore_text, (SIDE_PANEL_X + 10, y_offset + 360))

    def draw_probability_bar(self, player, percentage, y_position):
        """Draw a probability bar for a player"""
        # Set color based on player
        if player == "RED":
            color = RED
            text = "RED"
        elif player == "WHITE":
            color = WHITE
            text = "WHITE"
        else:
            color = LIGHT_GRAY
            text = "DRAW"
            
        # Draw label
        label = FONT_SMALL.render(text, True, color)
        self.win.blit(label, (SIDE_PANEL_X + 10, y_position))
        
        # Draw percentage
        pct_text = FONT_SMALL.render(f"{percentage:.1f}%", True, color)
        self.win.blit(pct_text, (SIDE_PANEL_X + 10, y_position + 25))
        
        # Draw bar background
        bar_width = WIDTH - SIDE_PANEL_X - 40
        pygame.draw.rect(self.win, (60, 60, 70), 
                       (SIDE_PANEL_X + 10, y_position + 50, 
                        bar_width, 20), 
                        border_radius=5)
        
        # Draw filled bar
        fill_width = int((percentage / 100) * bar_width)
        if fill_width > 0:
            pygame.draw.rect(self.win, color, 
                           (SIDE_PANEL_X + 10, y_position + 50, 
                            fill_width, 20), 
                            border_radius=5)

    def draw_ui(self):
        """Draw user interface elements"""
        # Draw turn indicator
        turn_text = "RED'S TURN" if self.turn == RED else "WHITE'S TURN"
        if self.game_mode == "human_vs_ai" and self.turn == self.ai_color:
            turn_text += " (AI Thinking...)" if self.ai_thinking else " (AI)"
        
        text_color = RED if self.turn == RED else WHITE
        text = FONT_MEDIUM.render(turn_text, True, text_color)
        text_rect = text.get_rect(center=(BOARD_OFFSET_X + BOARD_SIZE//2, HEIGHT - 40))
        
        # Draw background for turn indicator
        pygame.draw.rect(self.win, BLACK, 
                       (text_rect.x - 20, text_rect.y - 10, 
                        text_rect.width + 40, text_rect.height + 20), 
                       border_radius=10)
        self.win.blit(text, text_rect)
        
        # Draw piece counters
        red_text = FONT_SMALL.render(f"RED: {self.board.red_left}", True, RED)
        white_text = FONT_SMALL.render(f"WHITE: {self.board.white_left}", True, WHITE)
        self.win.blit(red_text, (BOARD_OFFSET_X, BOARD_OFFSET_Y - 30))
        self.win.blit(white_text, (BOARD_OFFSET_X + BOARD_SIZE - white_text.get_width(), BOARD_OFFSET_Y - 30))
        
        # Draw buttons if enabled
        if self.show_buttons:
            # Undo button
            pygame.draw.rect(self.win, BLUE if self.move_history else DARK_GRAY, self.buttons["undo"], border_radius=5)
            undo_text = FONT_SMALL.render("Undo", True, WHITE)
            undo_rect = undo_text.get_rect(center=self.buttons["undo"].center)
            self.win.blit(undo_text, undo_rect)
            
            # Redo button
            pygame.draw.rect(self.win, BLUE if self.future_moves else DARK_GRAY, self.buttons["redo"], border_radius=5)
            redo_text = FONT_SMALL.render("Redo", True, WHITE)
            redo_rect = redo_text.get_rect(center=self.buttons["redo"].center)
            self.win.blit(redo_text, redo_rect)
            
            # Menu button
            pygame.draw.rect(self.win, BLUE, self.buttons["menu"], border_radius=5)
            menu_text = FONT_SMALL.render("Menu", True, WHITE)
            menu_rect = menu_text.get_rect(center=self.buttons["menu"].center)
            self.win.blit(menu_text, menu_rect)
        
        # Draw winner message
        if self.game_over:
            self.display_winner()

    def draw_valid_moves(self):
        """Highlight valid moves for the selected piece with animation"""
        current_time = pygame.time.get_ticks()
        pulse_size = int(5 * (0.5 + 0.5 * abs(pygame.math.Vector2(0, 1).rotate(current_time / 5).y)))
        
        for move, skipped in self.valid_moves.items():
            row, col = move
            center_x = BOARD_OFFSET_X + col * SQUARE_SIZE + SQUARE_SIZE // 2
            center_y = BOARD_OFFSET_Y + row * SQUARE_SIZE + SQUARE_SIZE // 2
            
            # Draw pulsing green circle
            pygame.draw.circle(self.win, GREEN, (center_x, center_y), 15 + pulse_size)
            pygame.draw.circle(self.win, BLACK, (center_x, center_y), 15 + pulse_size, 1)

    def get_valid_moves(self, piece):
        """Calculate all valid moves for a piece"""
        moves = {}
        left = piece.col - 1
        right = piece.col + 1
        row = piece.row

        if piece.color == RED or piece.king:
            moves.update(self._traverse_left(row - 1, max(row - 3, -1), -1, piece.color, left))
            moves.update(self._traverse_right(row - 1, max(row - 3, -1), -1, piece.color, right))
        
        if piece.color == WHITE or piece.king:
            moves.update(self._traverse_left(row + 1, min(row + 3, ROWS), 1, piece.color, left))
            moves.update(self._traverse_right(row + 1, min(row + 3, ROWS), 1, piece.color, right))
        
        return moves

    def _traverse_left(self, start, stop, step, color, left, skipped=[]):
        moves = {}
        last = []
        for r in range(start, stop, step):
            if left < 0:
                break
            
            current = self.board.get_piece(r, left)
            if current == 0:
                if skipped and not last:
                    break
                elif skipped:
                    moves[(r, left)] = last + skipped
                else:
                    moves[(r, left)] = last
                
                if last:
                    if step == -1:
                        row = max(r - 3, -1)
                    else:
                        row = min(r + 3, ROWS)
                    moves.update(self._traverse_left(r + step, row, step, color, left - 1, skipped=last))
                    moves.update(self._traverse_right(r + step, row, step, color, left + 1, skipped=last))
                break
            elif current.color == color:
                break
            else:
                last = [current]
            
            left -= 1
        
        return moves

    def _traverse_right(self, start, stop, step, color, right, skipped=[]):
        moves = {}
        last = []
        for r in range(start, stop, step):
            if right >= COLS:
                break
            
            current = self.board.get_piece(r, right)
            if current == 0:
                if skipped and not last:
                    break
                elif skipped:
                    moves[(r, right)] = last + skipped
                else:
                    moves[(r, right)] = last
                
                if last:
                    if step == -1:
                        row = max(r - 3, -1)
                    else:
                        row = min(r + 3, ROWS)
                    moves.update(self._traverse_left(r + step, row, step, color, right - 1, skipped=last))
                    moves.update(self._traverse_right(r + step, row, step, color, right + 1, skipped=last))
                break
            elif current.color == color:
                break
            else:
                last = [current]
            
            right += 1
        
        return moves

    def get_row_col_from_mouse(self, pos):
        """Convert mouse position to board row and column"""
        x, y = pos
        
        # Check if click is within board boundaries
        if (BOARD_OFFSET_X <= x <= BOARD_OFFSET_X + BOARD_SIZE and 
            BOARD_OFFSET_Y <= y <= BOARD_OFFSET_Y + BOARD_SIZE):
            row = (y - BOARD_OFFSET_Y) // SQUARE_SIZE
            col = (x - BOARD_OFFSET_X) // SQUARE_SIZE
            if 0 <= row < ROWS and 0 <= col < COLS:
                return row, col
        
        return None

    def select(self, pos):
        """Handle piece selection and movement"""
        # Check if a button was clicked
        if self.show_buttons:
            for button_name, button_rect in self.buttons.items():
                if button_rect.collidepoint(pos):
                    if button_name == "undo":
                        return self.undo_move()
                    elif button_name == "redo":
                        return self.redo_move()
                    elif button_name == "menu":
                        return "menu"
        
        # Convert mouse position to board coordinates
        result = self.get_row_col_from_mouse(pos)
        if not result:  # Click was outside the board
            return False
            
        row, col = result
        
        if self.selected:
            result = self._move(row, col)
            if not result:
                self.selected.selected = False
                self.selected = None
                self.valid_moves = {}
                self.select(pos)  # Try selecting a new piece
        else:
            piece = self.board.get_piece(row, col)
            if piece != 0 and piece.color == self.turn:
                self.selected = piece
                self.selected.selected = True
                self.valid_moves = self.get_valid_moves(piece)
                return True
            
        return False

    def _move(self, row, col):
        """Move the selected piece to the specified position"""
        piece = self.board.get_piece(row, col)
        if self.selected and piece == 0 and (row, col) in self.valid_moves:
            # Store current state before making move
            self.store_move()
            
            # Get skipped pieces before making the move
            skipped = self.valid_moves[(row, col)]
            
            # Make the move
            self.board.move(self.selected, row, col)
            if skipped:
                self.board.remove(skipped)
            
            self.change_turn()
            return True
        return False
    
    def store_move(self):
        """Store the current game state for undo functionality"""
        current_state = {
            'board': self.board.copy(),
            'turn': self.turn,
            'game_over': self.game_over,
            'winner': self.winner
        }
        self.move_history.append(current_state)
        self.future_moves = []  # Clear redo history when a new move is made
    
    def undo_move(self):
        """Undo the last move"""
        if not self.move_history:
            return False
        
        # Store current state for redo
        current_state = {
            'board': self.board.copy(),
            'turn': self.turn,
            'game_over': self.game_over,
            'winner': self.winner
        }
        self.future_moves.append(current_state)
        
        # Restore previous state
        previous_state = self.move_history.pop()
        self.board = previous_state['board']
        self.turn = previous_state['turn']
        self.game_over = previous_state['game_over']
        self.winner = previous_state['winner']
        
        # Reset selection
        if self.selected:
            self.selected.selected = False
        self.selected = None
        self.valid_moves = {}
        
        return True
    
    def redo_move(self):
        """Redo a previously undone move"""
        if not self.future_moves:
            return False
        
        # Store current state for undo
        current_state = {
            'board': self.board.copy(),
            'turn': self.turn,
            'game_over': self.game_over,
            'winner': self.winner
        }
        self.move_history.append(current_state)
        
        # Restore future state
        future_state = self.future_moves.pop()
        self.board = future_state['board']
        self.turn = future_state['turn']
        self.game_over = future_state['game_over']
        self.winner = future_state['winner']
        
        # Reset selection
        if self.selected:
            self.selected.selected = False
        self.selected = None
        self.valid_moves = {}
        
        return True

    def change_turn(self):
        """Switch to the other player's turn"""
        if self.selected:
            self.selected.selected = False
        self.valid_moves = {}
        self.selected = None
        self.turn = WHITE if self.turn == RED else RED
        self.turn_indicator_time = pygame.time.get_ticks()
        self.check_winner()
        
        # Reset Monte Carlo results when turn changes
        self.monte_carlo_results = {"RED": 0, "WHITE": 0, "DRAW": 0}
        self.monte_carlo_total = 0
        
        # Auto-run Monte Carlo simulation if enabled and game is not over
        if self.auto_monte_carlo and not self.game_over:
            self.run_monte_carlo_simulation()

    def check_winner(self):
        """Check for a winner"""
        red_has_moves = False
        white_has_moves = False
        
        # Check if players have any valid moves
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.board.get_piece(row, col)
                if piece != 0:
                    if piece.color == RED:
                        moves = self.get_valid_moves(piece)
                        if moves:
                            red_has_moves = True
                    elif piece.color == WHITE:
                        moves = self.get_valid_moves(piece)
                        if moves:
                            white_has_moves = True
        
        if not red_has_moves or self.board.red_left <= 0:
            self.game_over = True
            self.winner = "WHITE WINS!"
            # Update Firebase stats for winner
            if self.firebase_auth and self.firebase_auth.local_id:
                if self.game_mode == "human_vs_ai" and self.ai_color == WHITE:
                    self.firebase_auth.update_user_stats(win=False)  # Human lost
                else:
                    self.firebase_auth.update_user_stats(win=(self.turn != RED))
                
        elif not white_has_moves or self.board.white_left <= 0:
            self.game_over = True
            self.winner = "RED WINS!"
            # Update Firebase stats for winner
            if self.firebase_auth and self.firebase_auth.local_id:
                if self.game_mode == "human_vs_ai" and self.ai_color == RED:
                    self.firebase_auth.update_user_stats(win=False)  # Human lost
                else:
                    self.firebase_auth.update_user_stats(win=(self.turn != WHITE))

    def display_winner(self):
        """Display winner message with animation"""
        if self.game_over:
            # Create semi-transparent overlay
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.win.blit(overlay, (0, 0))
            
            # Draw winner text with glow effect
            text = FONT_LARGE.render(self.winner, True, GOLD)
            text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2))
            
            # Create glow
            glow_size = int(10 * abs(pygame.math.Vector2(0, 1).rotate(pygame.time.get_ticks() / 3).y))
            for i in range(glow_size, 0, -2):
                glow_color = (255, 215, 0, 10 + i * 2)
                glow_text = FONT_LARGE.render(self.winner, True, glow_color)
                self.win.blit(glow_text, (text_rect.x, text_rect.y - glow_size + i))

            self.win.blit(text, text_rect)
            
            # Draw restart prompt
            restart_text = FONT_MEDIUM.render("🎮 Click to play again", True, WHITE)
            restart_rect = restart_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 60))
            self.win.blit(restart_text, restart_rect)
            
    def run_monte_carlo_simulation(self):
        """Run Monte Carlo simulation in a separate thread"""
        if self.monte_carlo_running:
            return
            
        self.monte_carlo_running = True
        self.monte_carlo_thread = threading.Thread(target=self._monte_carlo_worker)
        self.monte_carlo_thread.daemon = True
        self.monte_carlo_thread.start()
        
    def _monte_carlo_worker(self):
        """Worker function for Monte Carlo simulation"""
        try:
            # Reset results
            self.monte_carlo_results = {"RED": 0, "WHITE": 0, "DRAW": 0}
            self.monte_carlo_total = 0
            
            # Run simulations
            num_simulations = self.simulation_speed
            max_moves = 200  # Prevent infinite games
            
            for _ in range(num_simulations):
                # Create a copy of the current game state
                board_copy = self.board.copy()
                current_turn = self.turn
                move_count = 0
                
                # Play a random game until completion
                while True:
                    # Check for winner
                    red_pieces = board_copy.get_all_pieces(RED)
                    white_pieces = board_copy.get_all_pieces(WHITE)
                    
                    if not red_pieces:
                        self.monte_carlo_results["WHITE"] += 1
                        break
                    elif not white_pieces:
                        self.monte_carlo_results["RED"] += 1
                        break
                    
                    # Check for moves
                    valid_moves_exist = False
                    pieces = board_copy.get_all_pieces(current_turn)
                    random.shuffle(pieces)  # Randomize piece selection
                    
                    for piece in pieces:
                        moves = self._get_valid_moves_for_simulation(board_copy, piece)
                        if moves:
                            valid_moves_exist = True
                            # Choose a random move
                            move_pos, skipped = random.choice(list(moves.items()))
                            
                            # Execute the move
                            row, col = move_pos
                            board_copy.move(piece, row, col)
                            if skipped:
                                board_copy.remove(skipped)
                            break
                    
                    if not valid_moves_exist:
                        # Current player has no valid moves
                        if current_turn == RED:
                            self.monte_carlo_results["WHITE"] += 1
                        else:
                            self.monte_carlo_results["RED"] += 1
                        break
                    
                    # Switch turn
                    current_turn = WHITE if current_turn == RED else RED
                    move_count += 1
                    
                    # Check for draw (too many moves)
                    if move_count >= max_moves:
                        self.monte_carlo_results["DRAW"] += 1
                        break
                
                # Update total
                self.monte_carlo_total += 1
                
                # Update every 10 simulations to show progress
                if self.monte_carlo_total % 10 == 0:
                    time.sleep(0.01)  # Small delay to allow UI updates
        finally:
            self.monte_carlo_running = False
    
    def _get_valid_moves_for_simulation(self, board, piece):
        """Get valid moves for a piece in simulation (without modifying the game state)"""
        moves = {}
        left = piece.col - 1
        right = piece.col + 1
        row = piece.row

        if piece.color == RED or piece.king:
            moves.update(self._traverse_left_sim(board, row - 1, max(row - 3, -1), -1, piece.color, left))
            moves.update(self._traverse_right_sim(board, row - 1, max(row - 3, -1), -1, piece.color, right))
        
        if piece.color == WHITE or piece.king:
            moves.update(self._traverse_left_sim(board, row + 1, min(row + 3, ROWS), 1, piece.color, left))
            moves.update(self._traverse_right_sim(board, row + 1, min(row + 3, ROWS), 1, piece.color, right))
        
        return moves
        
    def _traverse_left_sim(self, board, start, stop, step, color, left, skipped=[]):
        moves = {}
        last = []
        for r in range(start, stop, step):
            if left < 0:
                break
            
            current = board.get_piece(r, left)
            if current == 0:
                if skipped and not last:
                    break
                elif skipped:
                    moves[(r, left)] = last + skipped
                else:
                    moves[(r, left)] = last
                
                if last:
                    if step == -1:
                        row = max(r - 3, -1)
                    else:
                        row = min(r + 3, ROWS)
                    moves.update(self._traverse_left_sim(board, r + step, row, step, color, left - 1, skipped=last))
                    moves.update(self._traverse_right_sim(board, r + step, row, step, color, left + 1, skipped=last))
                break
            elif current.color == color:
                break
            else:
                last = [current]
            
            left -= 1
        
        return moves

    def _traverse_right_sim(self, board, start, stop, step, color, right, skipped=[]):
        moves = {}
        last = []
        for r in range(start, stop, step):
            if right >= COLS:
                break
            
            current = board.get_piece(r, right)
            if current == 0:
                if skipped and not last:
                    break
                elif skipped:
                    moves[(r, right)] = last + skipped
                else:
                    moves[(r, right)] = last
                
                if last:
                    if step == -1:
                        row = max(r - 3, -1)
                    else:
                        row = min(r + 3, ROWS)
                    moves.update(self._traverse_left_sim(board, r + step, row, step, color, right - 1, skipped=last))
                    moves.update(self._traverse_right_sim(board, r + step, row, step, color, right + 1, skipped=last))
                break
            elif current.color == color:
                break
            else:
                last = [current]
            
            right += 1
        
        return moves
    
    def minimax(self, board, depth, alpha, beta, is_maximizing, is_red_player):
        """
        Minimax algorithm with alpha-beta pruning
        - board: current board state
        - depth: search depth
        - alpha, beta: bounds for pruning
        - is_maximizing: whether current player is maximizing
        - is_red_player: whether AI is playing as red
        """
        # Terminal conditions
        if depth == 0 or board.red_left == 0 or board.white_left == 0:
            return board.evaluate() if is_red_player else -board.evaluate(), None
        
        # Initialize best move
        best_move = None
        
        if is_maximizing:
            # Maximizing player
            max_eval = float('-inf')
            color = RED if is_red_player else WHITE
            
            # Get all valid moves for current player
            for piece in board.get_all_pieces(color):
                valid_moves = self.get_valid_moves(piece)
                
                # Try each move
                for move, skipped in valid_moves.items():
                    # Create temporary board
                    temp_board = board.copy()
                    temp_piece = temp_board.get_piece(piece.row, piece.col)
                    
                    if temp_piece != 0:  # Make sure piece is not 0
                        # Make move on temporary board
                        temp_board.move(temp_piece, move[0], move[1])
                        if skipped:
                            temp_board.remove(skipped)
                        
                        # Recursive evaluation
                        eval, _ = self.minimax(temp_board, depth - 1, alpha, beta, False, is_red_player)
                        
                        # Update best move
                        if eval > max_eval:
                            max_eval = eval
                            best_move = (piece, move)
                        
                        # Alpha-beta pruning
                        alpha = max(alpha, eval)
                        if beta <= alpha:
                            break
            
            return max_eval, best_move
        else:
            # Minimizing player
            min_eval = float('inf')
            color = WHITE if is_red_player else RED
            
            # Get all valid moves for opponent
            for piece in board.get_all_pieces(color):
                valid_moves = self.get_valid_moves(piece)
                
                # Try each move
                for move, skipped in valid_moves.items():
                    # Create temporary board
                    temp_board = board.copy()
                    temp_piece = temp_board.get_piece(piece.row, piece.col)
                    
                    if temp_piece != 0:  # Make sure piece is not 0
                        # Make move on temporary board
                        temp_board.move(temp_piece, move[0], move[1])
                        if skipped:
                            temp_board.remove(skipped)
                        
                        # Recursive evaluation
                        eval, _ = self.minimax(temp_board, depth - 1, alpha, beta, True, is_red_player)
                        
                        # Update best move
                        if eval < min_eval:
                            min_eval = eval
                            best_move = (piece, move)
                        
                        # Alpha-beta pruning
                        beta = min(beta, eval)
                        if beta <= alpha:
                            break
            
            return min_eval, best_move
    
    def ai_move(self):
        """Make a move for the AI using minimax algorithm"""
        # Set thinking depth based on difficulty
        if self.ai_difficulty == "easy":
            depth = 2
        elif self.ai_difficulty == "medium":
            depth = 4
        else:  # hard
            depth = 6
        
        # Use minimax to find best move
        is_red_player = self.ai_color == RED
        _, best_move = self.minimax(self.board, depth, float('-inf'), float('inf'), True, is_red_player)
        
        if best_move:
            piece, move = best_move
            row, col = move
            
            # Store current state for undo
            self.store_move()
            
            # Highlight AI's selected piece briefly
            self.selected = piece
            self.valid_moves = self.get_valid_moves(piece)
            self.selected.selected = True
            self.update()
            pygame.time.delay(500)  # Pause to show selection
            
            # Make the move
            self.board.move(piece, row, col)
            skipped = self.valid_moves.get((row, col), [])
            if skipped:
                self.board.remove(skipped)
            
            # Change turn
            self.change_turn()
            return True
        
        # No valid moves for AI
        return False

def main():
    """Main game loop"""
    # Initialize screen
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("AI CHECKERS MASTER")
    
    # Game state
    current_screen = "login"
    login_screen = LoginScreen(screen)
    game_menu = None
    game = None
    username = None
    firebase_auth = FirestoreAuth()
    
    # Main loop
    running = True
    clock = pygame.time.Clock()
    
    while running:
        clock.tick(60)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if current_screen == "login":
                result = login_screen.handle_event(event)
                if result:  # Successful login
                    username = result
                    game_menu = GameMenu(screen, username, firebase_auth)
                    current_screen = "menu"
            
            elif current_screen == "menu":
                result = game_menu.handle_event(event)
                if result == "start_game":
                    game = Game(screen, username, game_menu.game_mode, game_menu.ai_difficulty, firebase_auth=firebase_auth)
                    current_screen = "game"
                    # Run initial Monte Carlo simulation
                    game.run_monte_carlo_simulation()
                elif result == "logout":
                    login_screen = LoginScreen(screen)
                    current_screen = "login"
            
            elif current_screen == "game":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    
                    if not game.game_over:
                        result = game.select(pos)
                        if result == "menu":
                            current_screen = "menu"
                    else:
                        # Restart game if clicked after game over
                        game = Game(screen, username, game_menu.game_mode, game_menu.ai_difficulty, firebase_auth=firebase_auth)
                        # Run initial Monte Carlo simulation for new game
                        game.run_monte_carlo_simulation()
        
        # Draw current screen
        if current_screen == "login":
            login_screen.draw()
        elif current_screen == "menu":
            game_menu.draw()
        elif current_screen == "game":
            game.update()
        
        pygame.display.update()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    print("🎮 Starting AI Checkers Master with Enhanced Design...")
    print("✨ Beautiful animated UI with checkers theme")
    print("📧 Firebase authentication enabled")
    print("🤖 AI opponents with 3 difficulty levels")
    print("🎯 Monte Carlo win probability analysis")
    print("↩️ Undo/Redo functionality")
    print("💾 Data stored in Cloud Firestore")
    print("🎨 Enhanced visual design with animations")
    print("\n" + "="*60)
    print("FEATURES:")
    print("• 🎭 Animated login screen with floating checkers pieces")
    print("• 👑 Enhanced menu with beautiful checkers theme")
    print("• 📊 Detailed statistics tracking")
    print("• 🏆 Achievement badges for veteran players")
    print("• ✨ Smooth animations and visual effects")
    print("• 🎮 Professional game interface")
    print("="*60 + "\n")
    
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)
