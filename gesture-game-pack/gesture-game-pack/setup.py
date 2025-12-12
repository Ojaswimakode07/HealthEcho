"""
Universal Installation Script for 9-Game Gesture Hub
"""

import subprocess
import sys
import os
import platform
import venv
import importlib
from pathlib import Path

# -------------------------------------------------------
# COLOR OUTPUT
# -------------------------------------------------------
class Color:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"{Color.HEADER}{Color.BOLD}{'='*60}{Color.ENDC}")
    print(f"{Color.HEADER}{Color.BOLD}{text:^60}{Color.ENDC}")
    print(f"{Color.HEADER}{Color.BOLD}{'='*60}{Color.ENDC}")

def print_success(text):
    print(f"{Color.OKGREEN}✓ {text}{Color.ENDC}")

def print_info(text):
    print(f"{Color.OKBLUE}ℹ {text}{Color.ENDC}")

def print_warning(text):
    print(f"{Color.WARNING}⚠ {text}{Color.ENDC}")

def print_error(text):
    print(f"{Color.FAIL}✗ {text}{Color.ENDC}")

# -------------------------------------------------------
# DEPENDENCY INSTALLATION
# -------------------------------------------------------
def check_python_version():
    """Check if Python version is compatible"""
    print_info("Checking Python version...")
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 7):
        print_error(f"Python 3.7+ required (you have {major}.{minor})")
        return False
    print_success(f"Python {major}.{minor} detected")
    return True

def check_package(package_name):
    """Check if a package is already installed"""
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False

def install_package(package_spec):
    """Install a Python package"""
    package_name = package_spec.split('>=')[0].split('==')[0]
    
    if check_package(package_name):
        print_success(f"{package_name} already installed")
        return True
    
    print_info(f"Installing {package_spec}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_spec])
        print_success(f"{package_name} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install {package_name}: {e}")
        return False

# -------------------------------------------------------
# VIRTUAL ENVIRONMENT
# -------------------------------------------------------
def setup_virtual_environment():
    """Create and activate virtual environment"""
    print_header("VIRTUAL ENVIRONMENT SETUP")
    
    venv_path = Path("env")
    
    if venv_path.exists():
        print_info("Virtual environment already exists")
    else:
        print_info("Creating virtual environment...")
        try:
            venv.create(venv_path, with_pip=True)
            print_success("Virtual environment created")
        except Exception as e:
            print_error(f"Failed to create virtual environment: {e}")
            return False
    
    # Print activation instructions
    print_header("ACTIVATION INSTRUCTIONS")
    if platform.system() == "Windows":
        print("To activate on Windows:")
        print(f"  {venv_path}\\Scripts\\activate")
    else:
        print("To activate on macOS/Linux:")
        print(f"  source {venv_path}/bin/activate")
    
    print("\nAfter activation, run:")
    print("  python setup.py")
    
    return True

# -------------------------------------------------------
# GAME DETECTION
# -------------------------------------------------------
def detect_games():
    """Detect all available games in the games folder"""
    print_header("GAME DETECTION")
    
    games_dir = Path("games")
    
    # Create games directory if it doesn't exist
    if not games_dir.exists():
        games_dir.mkdir()
        (games_dir / "__init__.py").touch()
        print_info("Created games directory")
    
    # List all game files
    game_files = list(games_dir.glob("*_game.py"))
    
    if not game_files:
        print_warning("No game files found! Creating placeholder files...")
        create_placeholder_games(games_dir)
        game_files = list(games_dir.glob("*_game.py"))
    
    print_info(f"Found {len(game_files)} game(s):")
    for game_file in game_files:
        game_name = game_file.stem.replace("_game", "")
        print(f"  - {game_name.title()} Game")
    
    return len(game_files)

def create_placeholder_games(games_dir):
    """Create placeholder game files if none exist"""
    game_templates = {
        "snake_game.py": """
\"\"\"Snake Game - Nokia-style classic\"\"\"

import pygame
from game_manager import BaseGame

class SnakeGame(BaseGame):
    def __init__(self, width=800, height=600):
        super().__init__(width, height)
        self.title = "Snake Game"
        print(f"Initialized {self.title}")
    
    def handle_gesture(self, gesture_data):
        pass
    
    def update(self):
        pass
    
    def draw(self, surface=None):
        target = surface or self.screen
        target.fill((0, 0, 0))
        font = pygame.font.Font(None, 48)
        text = font.render(self.title, True, (255, 255, 255))
        target.blit(text, (self.width//2 - text.get_width()//2, 
                          self.height//2 - text.get_height()//2))
        
        if surface is None:
            pygame.display.flip()
""",
        "pong_game.py": """
\"\"\"Pong Game - Classic paddle game\"\"\"

import pygame
from game_manager import BaseGame

class PongGame(BaseGame):
    def __init__(self, width=800, height=600):
        super().__init__(width, height)
        self.title = "Pong Game"
        print(f"Initialized {self.title}")
    
    def handle_gesture(self, gesture_data):
        pass
    
    def update(self):
        pass
    
    def draw(self, surface=None):
        target = surface or self.screen
        target.fill((0, 0, 0))
        font = pygame.font.Font(None, 48)
        text = font.render(self.title, True, (255, 255, 255))
        target.blit(text, (self.width//2 - text.get_width()//2, 
                          self.height//2 - text.get_height()//2))
        
        if surface is None:
            pygame.display.flip()
"""
    }
    
    for filename, content in game_templates.items():
        file_path = games_dir / filename
        if not file_path.exists():
            file_path.write_text(content)
            print_info(f"Created {filename}")

# -------------------------------------------------------
# REQUIREMENTS MANAGEMENT
# -------------------------------------------------------
def install_dependencies():
    """Install all required dependencies"""
    print_header("DEPENDENCY INSTALLATION")
    
    # Core dependencies
    dependencies = [
        "opencv-python>=4.8.0",
        "mediapipe>=0.10.0",
        "numpy>=1.24.0",
        "pygame>=2.4.0",
        "pillow>=9.0.0"  # For image processing
    ]
    
    success_count = 0
    total_count = len(dependencies)
    
    for dep in dependencies:
        if install_package(dep):
            success_count += 1
    
    # Create requirements file
    with open("requirements.txt", "w") as f:
        f.write("\n".join(dependencies))
    print_success("Created requirements.txt")
    
    return success_count == total_count