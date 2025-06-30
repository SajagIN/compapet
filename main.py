import sys
import os
import random
import math
from PyQt5.QtWidgets import (
    QApplication, QLabel, QWidget, QPushButton, QVBoxLayout,
    QSystemTrayIcon, QMenu, QAction, QDesktopWidget, QStyle
)
from PyQt5.QtGui import QPixmap, QTransform, QIcon
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect

# --- Configuration ---
CAT_WIDTH = 120    # Desired width of the cat sprite
CAT_HEIGHT = 120 # Desired height of the cat sprite

ANIMATION_FRAME_RATE = 100 # Milliseconds per frame for animation updates (e.g., 100ms = 10 fps)
MOVEMENT_SPEED = 3          # Pixels per step when walking
MOVEMENT_CHANGE_DELAY = 3000 # How often the cat changes direction/state (milliseconds)

# New configuration for running behavior
RUN_SPEED_MULTIPLIER = 2.5 # Cat will run 2.5x faster than walk speed

# Threshold for distinguishing a click from a drag
CLICK_THRESHOLD = 5 # Pixels. If mouse moves less than this, it's a click.

# --- Sprite Assets Mapping ---
# This dictionary maps animation names to the number of frames they have.
# The script will then construct the full paths based on this.
# IMPORTANT: Assumes 'dog' assets have the same animation names and frame counts.
ANIMATION_FRAMES = {
    "Dead": 10, "Fall": 8, "Hurt": 10, "Idle": 10, "Jump": 8, "Run": 8, "Slide": 10, "Walk": 10
}


class CatCompanionApp(QWidget):
    """
    Main application window for the desktop cat companion.
    Handles cat animation, movement, and drag functionality.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desk Pet Companion")

        # --- Window Settings ---
        # Make the window frameless (no title bar, no borders)
        # Qt.WindowStaysOnTopHint ensures this window remains on top of other applications,
        # including generally staying above the taskbar on most OS configurations.
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # Make the background transparent, so only the cat image is visible
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Set initial window size based on cat sprite size
        self.resize(CAT_WIDTH, CAT_HEIGHT)

        # --- Cat Display ---
        self.cat_label = QLabel(self)
        self.cat_label.setGeometry(0, 0, CAT_WIDTH, CAT_HEIGHT)
        self.cat_label.setAlignment(Qt.AlignCenter)

        # --- Asset Management ---
        # Default asset type is 'cat'
        self.current_asset_type = 'cat'
        self.sprites = {} # Will be populated by _load_sprites

        # --- Animation State ---
        self.current_animation = 'Idle'
        self.current_frame_index = 0

        # --- Animation Timer ---
        # This timer controls how often the cat's sprite frame updates.
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._next_frame)
        self.animation_timer.start(ANIMATION_FRAME_RATE)

        # --- Movement State ---
        # Changed: Store current position as float for smooth movement
        self._current_x = 0.0
        self._current_y = 0.0
        self.cat_velocity_x = 0.0
        self.cat_velocity_y = 0.0
        self.moving_right = True # Tracks if the cat is moving right for sprite flipping

        # State for edge running behavior
        self.is_edge_running = False
        self.target_x = 0
        self.target_y = 0

        # New: State for sliding behavior
        self.is_sliding = False
        self.slide_target_pos = QPoint()

        # --- Movement Timer ---
        # This timer controls how often the cat's position is updated.
        # Running at ~60 FPS (16ms interval) for smooth movement.
        self.movement_timer = QTimer(self)
        self.movement_timer.timeout.connect(self._update_cat_position)
        self.movement_timer.start(16)

        # --- Random Behavior Timer ---
        # This timer controls when the cat's movement or state randomly changes.
        self.random_behavior_timer = QTimer(self)
        self.random_behavior_timer.timeout.connect(self._random_movement)
        # Random behavior starts only when not dragging/playing one-shot animation.
        # This timer will be started/stopped explicitly.

        # --- Drag & Click Functionality ---
        self.dragging = False # Flag to indicate if the window is being dragged
        self.offset = QPoint() # Stores the offset from mouse click to window corner
        self.mouse_press_pos = QPoint() # Stores global position of mouse press for click detection
        self.is_playing_one_shot_animation = False # Flag to indicate if a one-shot animation (e.g., Hurt) is playing

        # --- System Tray Setup ---
        self.tray_icon = QSystemTrayIcon(self)
        tray_icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'tray_icon.png')
        if os.path.exists(tray_icon_path):
            self.tray_icon.setIcon(QIcon(tray_icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))

        self.tray_icon.setToolTip("Desk Pet Companion")

        # Create the tray menu
        tray_menu = QMenu()

        # Show/Hide action - Initial text is "Hide Pet" because it starts visible
        self.toggle_visibility_action = QAction("Hide Pet", self)
        self.toggle_visibility_action.triggered.connect(self.toggle_visibility)
        tray_menu.addAction(self.toggle_visibility_action)

        tray_menu.addSeparator()

        # Pet Type Sub-menu
        pet_type_menu = QMenu("Change Pet Type", self)
        self.cat_action = QAction("Cat", self, checkable=True)
        self.dog_action = QAction("Dog", self, checkable=True)

        # Ensure only one is checked at a time
        self.cat_action.triggered.connect(lambda: self.change_pet_type('cat'))
        self.dog_action.triggered.connect(lambda: self.change_pet_type('dog'))

        pet_type_menu.addAction(self.cat_action)
        pet_type_menu.addAction(self.dog_action)
        tray_menu.addMenu(pet_type_menu)

        tray_menu.addSeparator()

        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        # Connect activated signal to handle double-click (or single-click depending on OS)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        # Load initial sprites (cat by default)
        self.change_pet_type(self.current_asset_type) # This will also set initial animation and position
        self._set_initial_position() # Ensure initial position is set after loading sprites

        # Initially show the main window instead of hiding it
        self.show()
        # Immediately start random movement if visible
        self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)


    def _get_asset_path(self, animation_name, frame_number):
        """
        Constructs the full path to a sprite asset based on the current_asset_type.
        """
        base_dir = os.path.dirname(__file__)
        return os.path.join(base_dir, 'assets', self.current_asset_type, f'{animation_name} ({frame_number}).png')

    def _load_sprites(self):
        """
        Loads all sprite QPixmaps into memory for quick access for the current_asset_type.
        Caches them to avoid loading from disk repeatedly.
        Each pixmap is scaled to the desired CAT_WIDTH and CAT_HEIGHT.
        Returns a dictionary of loaded sprites.
        """
        all_sprites = {}
        asset_dir = os.path.join(os.path.dirname(__file__), 'assets', self.current_asset_type)

        if not os.path.exists(asset_dir) or not os.path.isdir(asset_dir):
            print(f"Error: Asset directory '{self.current_asset_type}' not found at '{asset_dir}'.\n"
                   "Please ensure your sprite assets are correctly placed.")
            return {} # Return empty if directory is missing

        for anim_name, num_frames in ANIMATION_FRAMES.items():
            all_sprites[anim_name] = []
            for i in range(1, num_frames + 1):
                path = self._get_asset_path(anim_name, i)
                try:
                    pixmap = QPixmap(path)
                    if pixmap.isNull():
                        print(f"Warning: Could not load sprite from {path}")
                    else:
                        all_sprites[anim_name].append(pixmap.scaled(
                            CAT_WIDTH, CAT_HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation
                        ))
                except Exception as e:
                    print(f"Error loading {path}: {e}")
        return all_sprites

    def change_pet_type(self, pet_type):
        """
        Changes the current pet type and reloads the sprites.
        """
        # Uncheck previous action
        if self.current_asset_type == 'cat':
            self.cat_action.setChecked(False)
        elif self.current_asset_type == 'dog':
            self.dog_action.setChecked(False)

        self.current_asset_type = pet_type
        self.sprites = self._load_sprites()

        if self.sprites: # Only set animation if sprites were successfully loaded
            self._set_animation('Idle')
            # Check the current action
            if self.current_asset_type == 'cat':
                self.cat_action.setChecked(True)
            elif self.current_asset_type == 'dog':
                self.dog_action.setChecked(True)
        else:
            # If loading failed, revert to default or handle error
            self.cat_label.setText(f"Error: No {pet_type} sprites found.")
            self.animation_timer.stop()
            self.movement_timer.stop()
            self.random_behavior_timer.stop()
            # Optionally revert to 'cat' if dog failed, and notify
            if pet_type == 'dog':
                self.current_asset_type = 'cat' # Revert to previous working state
                self.cat_action.setChecked(True)
                print(f"Failed to load 'dog' sprites. Reverted to 'cat'.")


    def _set_initial_position(self):
        """
        Sets the cat's initial position randomly on the screen and updates
        the floating-point position attributes.
        """
        screen_rect = QApplication.desktop().screenGeometry()
        max_x = screen_rect.width() - self.width()
        max_y = screen_rect.height() - self.height()
        initial_x = random.randint(0, max_x)
        initial_y = random.randint(0, max_y)
        self._current_x = float(initial_x) # Initialize float position
        self._current_y = float(initial_y) # Initialize float position
        self.move(int(self._current_x), int(self._current_y))

    def _set_animation(self, new_animation_name):
        """
        Changes the current animation state of the cat.
        Resets frame index when animation changes to start from the beginning of the new animation.
        """
        # If a one-shot animation is playing, do not interrupt it with other animations
        if self.is_playing_one_shot_animation and new_animation_name != self.current_animation:
            return

        # Fallback if the requested animation doesn't exist or has no frames for the current pet type
        if new_animation_name not in self.sprites or not self.sprites[new_animation_name]:
            print(f"Error: Animation '{new_animation_name}' not found or has no frames for {self.current_asset_type}. Falling back to Idle.")
            new_animation_name = 'Idle'
            if 'Idle' not in self.sprites or not self.sprites['Idle']:
                self.cat_label.setText(f"Error: No {self.current_asset_type} sprites loaded! Check assets folder.")
                self.animation_timer.stop()
                self.movement_timer.stop()
                self.random_behavior_timer.stop()
                return

        if self.current_animation != new_animation_name:
            self.current_animation = new_animation_name
            self.current_frame_index = 0
            # Update image immediately to show the first frame of the new animation
            self._update_cat_pixmap()

    def _next_frame(self):
        """Advances the animation to the next frame."""
        sprites = self.sprites.get(self.current_animation)
        if sprites:
            self.current_frame_index = (self.current_frame_index + 1) % len(sprites)
            self._update_cat_pixmap()
        else:
            self.cat_label.clear() # Clear the pixmap if no valid sprite to display

    def _update_cat_pixmap(self):
        """
        Updates the QPixmap displayed in the QLabel.
        Applies horizontal flipping based on movement direction.
        """
        sprites = self.sprites.get(self.current_animation)
        if sprites and self.current_frame_index < len(sprites):
            pixmap = sprites[self.current_frame_index]
            # Apply horizontal flip using QTransform if moving left
            if not self.moving_right:
                pixmap = pixmap.transformed(QTransform().scale(-1, 1))
            self.cat_label.setPixmap(pixmap)
        else:
            self.cat_label.clear()

    def _update_cat_position(self):
        """
        Updates the cat's position based on its velocity and handles screen edge collisions.
        Also handles stopping for one-shot animations and sliding behavior.
        """
        # Do not move if dragging, playing one-shot animation, or currently sliding
        if self.dragging or self.is_playing_one_shot_animation:
            return

        # Update floating-point position
        self._current_x += self.cat_velocity_x
        self._current_y += self.cat_velocity_y

        screen_rect = QApplication.desktop().screenGeometry()
        max_x = screen_rect.width() - self.width()
        max_y = screen_rect.height() - self.height()

        if self.is_sliding:
            # Check if target is reached or passed within a small tolerance
            target_reached_x = False
            if self.cat_velocity_x > 0 and self._current_x >= self.slide_target_pos.x():
                target_reached_x = True
            elif self.cat_velocity_x < 0 and self._current_x <= self.slide_target_pos.x():
                target_reached_x = True
            elif abs(self.cat_velocity_x) < 0.1: # If velocity is near zero, consider X target reached
                target_reached_x = True

            target_reached_y = False
            if self.cat_velocity_y > 0 and self._current_y >= self.slide_target_pos.y():
                target_reached_y = True
            elif self.cat_velocity_y < 0 and self._current_y <= self.slide_target_pos.y():
                target_reached_y = True
            elif abs(self.cat_velocity_y) < 0.1: # If velocity is near zero, consider Y target reached
                target_reached_y = True

            # Ensure it stops exactly at the target, clamping to screen bounds
            # This logic needs to consider the specific case of horizontal vs. diagonal slide
            # If sliding horizontally, only X matters for target reached, Y is fixed
            if self.cat_velocity_y == 0: # Purely horizontal slide
                if target_reached_x:
                    self._current_x = float(self.slide_target_pos.x())
                    self.is_sliding = False
            else: # Diagonal slide (or potentially vertical, though not explicitly chosen now)
                if target_reached_x and target_reached_y:
                    self._current_x = float(self.slide_target_pos.x())
                    self._current_y = float(self.slide_target_pos.y())
                    self.is_sliding = False

            # If sliding is finished, reset velocity and resume random movement
            if not self.is_sliding:
                self.cat_velocity_x = 0.0
                self.cat_velocity_y = 0.0
                self._set_animation('Idle')
                self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY) # Resume random movement
            else:
                # Clamp to screen bounds *during* movement to prevent it from going off-screen
                # before reaching the target if the target is close to the edge.
                self._current_x = max(0.0, min(self._current_x, float(max_x)))
                self._current_y = max(0.0, min(self._current_y, float(max_y)))
                self.move(int(self._current_x), int(self._current_y)) # Apply float position, converting to int
                if self.cat_velocity_x > 0:
                    self.moving_right = True
                elif self.cat_velocity_x < 0:
                    self.moving_right = False
                self._set_animation('Slide') # Keep showing slide animation


        elif self.is_edge_running:
            # Clamp to screen bounds and convert to int for move()
            self._current_x = max(0.0, min(self._current_x, float(max_x)))
            self._current_y = max(0.0, min(self._current_y, float(max_y)))
            self.move(int(self._current_x), int(self._current_y))

            # Check if target is reached or passed within a small tolerance
            target_reached_x = False
            if self.cat_velocity_x > 0 and self._current_x >= self.target_x:
                target_reached_x = True
            elif self.cat_velocity_x < 0 and self._current_x <= self.target_x:
                target_reached_x = True
            elif abs(self.cat_velocity_x) < 0.1: # If velocity is near zero, consider X target reached
                target_reached_x = True

            target_reached_y = False
            if self.cat_velocity_y > 0 and self._current_y >= self.target_y:
                target_reached_y = True
            elif self.cat_velocity_y < 0 and self._current_y <= self.target_y:
                target_reached_y = True
            elif abs(self.cat_velocity_y) < 0.1: # If velocity is near zero, consider Y target reached
                target_reached_y = True

            # If the cat hits any screen boundary during an edge run, or reaches its specific target
            # consider the run complete.
            hit_boundary = (self._current_x <= 0 or self._current_x >= max_x or self._current_y <= 0 or self._current_y >= max_y)

            if (target_reached_x and target_reached_y) or hit_boundary:
                self.is_edge_running = False
                self.cat_velocity_x = 0.0 # Stop movement
                self.cat_velocity_y = 0.0 # Stop movement
                self._set_animation('Idle') # Set to idle animation
                # The random_behavior_timer will automatically trigger _random_movement after its delay
            else:
                # If still running, ensure sprite orientation is correct
                if self.cat_velocity_x > 0:
                    self.moving_right = True
                elif self.cat_velocity_x < 0:
                    self.moving_right = False
                self._set_animation('Run') # Keep showing run animation

        else: # Normal Walk/Idle behavior with bouncing
            bounced = False

            # Horizontal collision
            if self._current_x < 0:
                self._current_x = 0.0 # Clamp to 0
                self.cat_velocity_x *= -1 # Reverse direction
                bounced = True
            elif self._current_x > max_x:
                self._current_x = float(max_x) # Clamp to max_x
                self.cat_velocity_x *= -1 # Reverse direction
                bounced = True

            # Vertical collision
            if self._current_y < 0:
                self._current_y = 0.0 # Clamp to 0
                self.cat_velocity_y *= -1 # Reverse direction
                bounced = True
            elif self._current_y > max_y:
                self._current_y = float(max_y) # Clamp to max_y
                self.cat_velocity_y *= -1 # Reverse direction
                bounced = True

            self.move(int(self._current_x), int(self._current_y)) # Apply new position to the window, casting to int

            # Update 'moving_right' flag for correct sprite flipping
            if self.cat_velocity_x > 0:
                self.moving_right = True
            elif self.cat_velocity_x < 0:
                self.moving_right = False

            # Adjust animation based on movement state
            # Only change animation if not currently playing a one-shot animation
            if not self.is_playing_one_shot_animation:
                if bounced and (abs(self.cat_velocity_x) > 0.1 or abs(self.cat_velocity_y) > 0.1):
                    self._set_animation('Walk') # Cat should be walking after a bounce
                elif not bounced and abs(self.cat_velocity_x) < 0.1 and abs(self.cat_velocity_y) < 0.1 and self.current_animation != 'Idle':
                    self._set_animation('Idle') # If stopped, go to idle
                elif not bounced and (abs(self.cat_velocity_x) > 0.1 or abs(self.cat_velocity_y) > 0.1) and self.current_animation != 'Walk':
                    self._set_animation('Walk') # If moving, go to walk

    def _random_movement(self):
        """
        Randomly sets the cat's movement state (Idle, Walk, Run to Edge, or Slide).
        Determines new velocity for walking/running/sliding or stops movement for idling.
        Will not run if a one-shot animation is playing or if already sliding.
        """
        if self.is_playing_one_shot_animation or self.is_sliding:
            return

        random_choice = random.random()

        # Probabilities adjusted: Run to Edge (15%), Slide (15%), Walk (50%), Idle (20%)
        if 'Run' in self.sprites and self.sprites['Run'] and random_choice < 0.15: # 15% chance to run to an edge
            self._start_edge_run()
        elif 'Slide' in self.sprites and self.sprites['Slide'] and random_choice < 0.30: # 15% chance to slide (0.15 to 0.30)
            self._start_slide_behavior()
        elif random_choice < 0.80: # 50% chance to walk (0.30 to 0.80)
            # Generate a random angle and calculate X, Y velocities for walking
            angle = random.uniform(0, 2 * math.pi) # Angle in radians (0 to 2*PI)
            # Calculate float velocities
            vx = MOVEMENT_SPEED * random.uniform(0.7, 1.3) * math.cos(angle)
            vy = MOVEMENT_SPEED * random.uniform(0.7, 1.3) * math.sin(angle)

            # Ensure velocities are not both too close to zero for walking
            if abs(vx) < 0.1 and abs(vy) < 0.1: # Small threshold
                # If both are very small, force a movement in a random cardinal direction
                if random.random() < 0.5:
                    vx = MOVEMENT_SPEED * random.choice([-1, 1])
                    vy = 0.0
                else:
                    vx = 0.0
                    vy = MOVEMENT_SPEED * random.choice([-1, 1])

            self.cat_velocity_x = vx # Keep as float
            self.cat_velocity_y = vy # Keep as float

            self._set_animation('Walk')
        else: # 20% chance to idle (0.80 to 1.00)
            self.cat_velocity_x = 0.0
            self.cat_velocity_y = 0.0
            self._set_animation('Idle')


    def _start_edge_run(self):
        """
        Initiates the 'run to edge' behavior.
        Calculates the velocity to move from the cat's current floating-point position
        towards a random point on a randomly chosen edge of the screen.
        """
        screen_rect = QApplication.desktop().screenGeometry()
        screen_width = screen_rect.width()
        screen_height = screen_rect.height()

        edges = ['top', 'bottom', 'left', 'right']
        # Choose a random edge for the target destination
        end_edge = random.choice(edges)

        # Calculate target position on the chosen end edge
        target_x, target_y = 0, 0
        if end_edge == 'top':
            target_x = random.randint(0, screen_width - CAT_WIDTH)
            target_y = 0
        elif end_edge == 'bottom':
            target_x = random.randint(0, screen_width - CAT_WIDTH)
            target_y = screen_height - CAT_HEIGHT
        elif end_edge == 'left':
            target_x = 0
            target_y = random.randint(0, screen_height - CAT_HEIGHT)
        elif end_edge == 'right':
            target_x = screen_width - CAT_WIDTH
            target_y = random.randint(0, screen_height - CAT_HEIGHT)

        # Calculate vector (dx, dy) from current floating-point position to target
        dx = float(target_x) - self._current_x
        dy = float(target_y) - self._current_y
        distance = math.sqrt(dx*dx + dy*dy) # Calculate Euclidean distance

        # Use a small epsilon to avoid division by zero if points are identical or very close
        if distance < 1.0:
            self.cat_velocity_x = 0.0
            self.cat_velocity_y = 0.0
            self.is_edge_running = False
            self._set_animation('Idle')
            return

        # Calculate velocities scaled by RUN_SPEED_MULTIPLIER
        self.cat_velocity_x = (dx / distance) * MOVEMENT_SPEED * RUN_SPEED_MULTIPLIER
        self.cat_velocity_y = (dy / distance) * MOVEMENT_SPEED * RUN_SPEED_MULTIPLIER

        self.is_edge_running = True # Set the flag to indicate edge running state
        self.target_x = target_x    # Store the target coordinates (as integers for direct comparison later)
        self.target_y = target_y
        self._set_animation('Run') # Set the 'Run' animation

        # Adjust 'moving_right' flag for initial orientation
        if self.cat_velocity_x > 0:
            self.moving_right = True
        elif self.cat_velocity_x < 0:
            self.moving_right = False

    def _start_slide_behavior(self):
        """
        Initiates the 'slide' behavior. The pet will slide purely horizontally
        or diagonally downwards.
        """
        screen_rect = QApplication.desktop().screenGeometry()
        screen_width = screen_rect.width()
        screen_height = screen_rect.height()

        # Decide between purely horizontal slide or diagonal downward slide
        slide_type = random.choice(['horizontal', 'diagonal_down'])

        target_x, target_y = 0, 0

        if slide_type == 'horizontal':
            # Target Y is the same as current Y for horizontal movement
            target_y = int(self._current_y) # Keep Y constant
            
            # Choose a target X different from current X
            # Try to slide to the right if on left half, or left if on right half
            if self._current_x < screen_width / 2: 
                potential_target_x = random.randint(int(self._current_x + 50), screen_width - CAT_WIDTH)
            else: 
                potential_target_x = random.randint(0, int(self._current_x - 50))
            
            # Fallback if the chosen range is invalid (e.g., already at edge)
            if potential_target_x < 0 or potential_target_x > screen_width - CAT_WIDTH:
                 target_x = random.randint(0, screen_width - CAT_WIDTH) # Any valid X
            else:
                target_x = potential_target_x


        elif slide_type == 'diagonal_down':
            # Target Y must be below current Y, ensuring downward movement
            min_target_y = int(self._current_y + 50) # At least 50 pixels down from current Y
            target_y = random.randint(min_target_y, screen_height - CAT_HEIGHT)

            # Target X can be left or right of current X, ensuring some horizontal movement
            direction_x = random.choice([-1, 1]) # -1 for left, 1 for right
            if direction_x == 1: # Slide down-right
                potential_target_x = random.randint(int(self._current_x + 10), screen_width - CAT_WIDTH)
            else: # Slide down-left
                potential_target_x = random.randint(0, int(self._current_x - 10))

            # Fallback if the chosen range is invalid
            if potential_target_x < 0 or potential_target_x > screen_width - CAT_WIDTH:
                 target_x = random.randint(0, screen_width - CAT_WIDTH) # Any valid X
            else:
                target_x = potential_target_x

        # Calculate vector (dx, dy) from current floating-point position to target
        dx = float(target_x) - self._current_x
        dy = float(target_y) - self._current_y
        distance = math.sqrt(dx*dx + dy*dy)

        # Ensure there's actual distance to slide to prevent division by zero
        if distance < 1.0:
            self.cat_velocity_x = 0.0
            self.cat_velocity_y = 0.0
            self.is_sliding = False
            self._set_animation('Idle')
            return

        # Use a slightly slower speed for sliding than running for a smoother effect
        slide_speed = MOVEMENT_SPEED * 1.5 # Example: 1.5x walk speed

        self.cat_velocity_x = (dx / distance) * slide_speed
        self.cat_velocity_y = (dy / distance) * slide_speed

        self.is_sliding = True
        self.slide_target_pos = QPoint(target_x, target_y) # Store target as QPoint
        self._set_animation('Slide')

        # Adjust 'moving_right' flag for initial orientation during slide
        if self.cat_velocity_x > 0:
            self.moving_right = True
        elif self.cat_velocity_x < 0:
            self.moving_right = False


    # --- Mouse Events for Dragging & Clicking ---
    def mousePressEvent(self, event):
        """Handles mouse button press events for dragging the window or starting a click."""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            # Store the global position of the mouse when the button is pressed
            self.mouse_press_pos = event.globalPos()
            # Calculate the offset from the window's top-left corner to the mouse click position
            self.offset = event.pos()
            # Stop random movement and set to Idle when dragging begins
            self.random_behavior_timer.stop() # Temporarily stop random movement changes
            self.cat_velocity_x = 0.0 # Stop current movement
            self.cat_velocity_y = 0.0
            self._set_animation('Idle') # Cat idles while being dragged
            # If it was in an edge run or sliding, also reset that state
            self.is_edge_running = False
            self.is_sliding = False # Stop sliding if initiated by drag

    def mouseMoveEvent(self, event):
        """Handles mouse movement events while dragging the window."""
        if self.dragging:
            # Move the window based on the current mouse position relative to the initial click offset
            self.move(self.mapToGlobal(event.pos() - self.offset))
            # Update float position attributes while dragging
            global_pos = self.mapToGlobal(event.pos() - self.offset)
            self._current_x = float(global_pos.x())
            self._current_y = float(global_pos.y())

    def mouseReleaseEvent(self, event):
        """Handles mouse button release events after dragging or clicking."""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            # Calculate the distance moved from the initial press point
            mouse_release_pos = event.globalPos()
            distance_moved = (mouse_release_pos - self.mouse_press_pos).manhattanLength() # Or .length() for Euclidean

            # If the distance moved is less than the threshold, it's a click
            if distance_moved < CLICK_THRESHOLD:
                # This is a click, not a drag-and-drop
                self._play_one_shot_animation('Hurt')
            else:
                # This was a drag-and-drop, simply restart normal movement
                self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)

    def _play_one_shot_animation(self, animation_name):
        """
        Plays a specific animation once and then returns to idle/random movement.
        Prevents other animations from interrupting.
        """
        if animation_name not in self.sprites or not self.sprites[animation_name]:
            print(f"Warning: Cannot play one-shot animation '{animation_name}'. Sprites not found.")
            # If animation is missing, just revert to normal behavior
            self.is_playing_one_shot_animation = False
            self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)
            return

        self.is_playing_one_shot_animation = True
        self.random_behavior_timer.stop() # Stop random movements
        self.cat_velocity_x = 0.0
        self.cat_velocity_y = 0.0

        # Set the animation
        self.current_animation = animation_name
        self.current_frame_index = 0
        self._update_cat_pixmap()

        # Calculate duration for the one-shot animation
        duration_ms = len(self.sprites[animation_name]) * ANIMATION_FRAME_RATE

        # Set a single-shot timer to revert state after the animation plays
        QTimer.singleShot(duration_ms, self._one_shot_animation_finished)

    def _one_shot_animation_finished(self):
        """Called when a one-shot animation completes."""
        self.is_playing_one_shot_animation = False
        self._set_animation('Idle') # Revert to idle after one-shot animation
        self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY) # Resume random movements


    def closeEvent(self, event):
        """
        Custom close event. Handles app exit gracefully, hiding the window and
        showing the tray icon, or quitting if explicitly from tray menu.
        """
        # If the app is quit from the tray menu, sys.exit() is called.
        # If the user tries to close the window normally, we just hide it to tray.
        if QApplication.quitOnLastWindowClosed():
            self.tray_icon.hide()
            event.accept()
        else:
            event.ignore()
            self.hide() # Hide to tray
            self.tray_icon.showMessage(
                "Desk Pet Companion",
                "The application is still running in the system tray. Click the icon to show/hide or exit.",
                QSystemTrayIcon.Information,
                2000
            )

    def toggle_visibility(self):
        """Toggles the visibility of the main application window."""
        if self.isVisible():
            self.hide()
            self.toggle_visibility_action.setText("Show Pet")
            # When hiding, stop movement and go to idle
            self.random_behavior_timer.stop()
            self.cat_velocity_x = 0.0
            self.cat_velocity_y = 0.0
            self._set_animation('Idle')
        else:
            self.show()
            self.toggle_visibility_action.setText("Hide Pet")
            # When showing, restart random movement (unless a one-shot animation or slide is active)
            if not self.is_playing_one_shot_animation and not self.is_sliding:
                self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)


    def on_tray_icon_activated(self, reason):
        """Handles clicks on the system tray icon."""
        if reason == QSystemTrayIcon.Trigger: # Left-click
            self.toggle_visibility()
        # On right-click (QSystemTrayIcon.Context), the context menu is automatically shown.


# --- Main Execution ---
if __name__ == '__main__':
    # Enable high DPI scaling for better appearance on high-resolution monitors.
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps) # Use high DPI pixmaps where available

    app = QApplication(sys.argv)
    # Ensure the application quits when the last window is closed,
    # unless it's explicitly hidden to the tray.
    # We will control this behavior in closeEvent.
    app.setQuitOnLastWindowClosed(False)


    # Check if a minimal assets directory structure exists
    base_dir = os.path.dirname(__file__)
    # For initial check, ensure at least 'assets/cat' exists.
    # The individual asset type loading will handle 'dog' specifically.
    initial_asset_check_dir = os.path.join(base_dir, 'assets', 'cat')

    if not os.path.exists(initial_asset_check_dir) or not os.path.isdir(initial_asset_check_dir):
        # Create a temporary QApplication to show error in console and exit
        print(f"Error: Default 'assets/cat' directory not found at '{initial_asset_check_dir}'.\n"
              "Please ensure your sprite assets are correctly placed.")
        sys.exit(1) # Exit with an error code

    # Initialize and show the main application window
    cat_app = CatCompanionApp()

    # Show an initial message to the user via the tray icon's message bubble.
    cat_app.tray_icon.showMessage(
        "Desk Pet Companion Started",
        "The application is running in the system tray. Click the icon to show/hide your pet.",
        QSystemTrayIcon.Information,
        3000
    )

    sys.exit(app.exec_()) # Start the Qt event loop
