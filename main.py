import sys
import os
import random
import math
from PyQt5.QtWidgets import (
    QApplication, QLabel, QWidget, QPushButton, QVBoxLayout,
    QSystemTrayIcon, QMenu, QAction, QDesktopWidget, QStyle # Added QStyle import here
)
from PyQt5.QtGui import QPixmap, QTransform, QIcon # QIcon needed for tray icon
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect

# --- Configuration ---
CAT_WIDTH = 120    # Desired width of the cat sprite
CAT_HEIGHT = 120 # Desired height of the cat sprite

ANIMATION_FRAME_RATE = 100 # Milliseconds per frame for animation updates (e.g., 100ms = 10 fps)
MOVEMENT_SPEED = 3          # Pixels per step when walking
MOVEMENT_CHANGE_DELAY = 3000 # How often the cat changes direction/state (milliseconds)

# New configuration for running behavior
RUN_SPEED_MULTIPLIER = 2.5 # Cat will run 2.5x faster than walk speed

# --- Sprite Assets Mapping ---
# This dictionary maps animation names to the number of frames they have.
# The script will then construct the full paths based on this.
# IMPORTANT: Assumes 'dog' assets have the same animation names and frame counts.
ANIMATION_FRAMES = {
    "Dead": 10, "Fall": 8, "Hurt": 10, "Idle": 10, "Jump": 8, "Run": 8, "Slide": 10, "Walk": 10
}

# --- Utility Function for Message Box (replacing alert()) ---
class MessageBox(QWidget):
    """
    A simple custom message box to display information to the user,
    as traditional alert() is not suitable for PyQt applications.
    This message box also uses the Qt.WindowStaysOnTopHint to ensure
    it appears above other windows.
    """
    def __init__(self, message, parent=None):
        super().__init__(parent, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Dialog)
        self.setWindowTitle("Information")
        # Make the background translucent for a modern look.
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.95); /* Semi-transparent white background */
                border-radius: 10px; /* Rounded corners */
                padding: 20px;
                font-family: 'Inter', sans-serif; /* Use Inter font */
                font-size: 14px;
                color: #333;
            }
            QLabel {
                color: #333; /* Dark text for message */
                margin-bottom: 10px;
            }
            QPushButton {
                background-color: #007bff; /* Blue button */
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3; /* Darker blue on hover */
            }
        """)

        # Use QVBoxLayout for simple vertical arrangement
        layout = QVBoxLayout(self)
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.message_label)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.close) # Close the message box when OK is clicked
        layout.addWidget(self.ok_button)

        self.adjustSize() # Adjust window size to fit content
        # Center the message box on the screen relative to its parent or desktop
        if parent:
            self.move(parent.mapToGlobal(parent.rect().center() - self.rect().center()))
        else:
            screen_rect = QApplication.desktop().screenGeometry()
            self.move(screen_rect.center() - self.rect().center())


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
        self.cat_velocity_x = 0.0 # Changed to float for smoother movement calculation
        self.cat_velocity_y = 0.0 # Changed to float for smoother movement calculation
        self.moving_right = True # Tracks if the cat is moving right for sprite flipping

        # New state for edge running behavior
        self.is_edge_running = False
        self.target_x = 0
        self.target_y = 0

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
        self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)

        # --- Drag Functionality ---
        self.dragging = False # Flag to indicate if the window is being dragged
        self.offset = QPoint() # Stores the offset from mouse click to window corner

        # --- System Tray Setup ---
        self.tray_icon = QSystemTrayIcon(self)
        # Placeholder icon: you should replace 'tray_icon.png' with an actual icon
        # for your app (e.g., a small cat/dog icon). For now, using a generic one.
        # Ideally, create a 16x16 or 24x24 pixel icon for the tray.
        # For simplicity, let's use a very basic icon for demonstration.
        # If 'assets/tray_icon.png' doesn't exist, this will default to a blank icon.
        tray_icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'tray_icon.png')
        if os.path.exists(tray_icon_path):
            self.tray_icon.setIcon(QIcon(tray_icon_path))
        else:
            # Fallback for missing tray icon (e.g., a default system icon or a placeholder)
            # Corrected: Used self.style() from QWidget, which needs QStyle imported
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon)) # Example placeholder

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
            MessageBox(f"Error: Asset directory '{self.current_asset_type}' not found at '{asset_dir}'.\n"
                       f"Please ensure '{self.current_asset_type}' sprites are correctly placed.", parent=self).show()
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
                MessageBox(f"Failed to load 'dog' sprites. Reverted to 'cat'.", parent=self).show()


    def _set_initial_position(self):
        """Sets the cat's initial position randomly on the screen."""
        screen_rect = QApplication.desktop().screenGeometry()
        max_x = screen_rect.width() - self.width()
        max_y = screen_rect.height() - self.height()
        initial_x = random.randint(0, max_x)
        initial_y = random.randint(0, max_y)
        self.move(initial_x, initial_y)

    def _set_animation(self, new_animation_name):
        """
        Changes the current animation state of the cat.
        Resets frame index when animation changes to start from the beginning of the new animation.
        """
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
        """
        if self.dragging:
            return # Position is handled by mouseMoveEvent when dragging

        current_x = self.x()
        current_y = self.y()

        new_x = current_x + self.cat_velocity_x
        new_y = current_y + self.cat_velocity_y

        # Using QDesktopWidget().screenGeometry() for screen dimensions for compatibility
        screen_rect = QApplication.desktop().screenGeometry()
        max_x = screen_rect.width() - self.width()
        max_y = screen_rect.height() - self.height()

        if self.is_edge_running:
            # Clamp to screen bounds and convert to int for move()
            new_x = max(0.0, min(new_x, float(max_x)))
            new_y = max(0.0, min(new_y, float(max_y)))
            self.move(int(new_x), int(new_y))

            # Check if target is reached or passed within a small tolerance
            target_reached_x = False
            if self.cat_velocity_x > 0 and new_x >= self.target_x:
                target_reached_x = True
            elif self.cat_velocity_x < 0 and new_x <= self.target_x:
                target_reached_x = True
            elif abs(self.cat_velocity_x) < 0.1: # If velocity is near zero, consider X target reached
                target_reached_x = True

            target_reached_y = False
            if self.cat_velocity_y > 0 and new_y >= self.target_y:
                target_reached_y = True
            elif self.cat_velocity_y < 0 and new_y <= self.target_y:
                target_reached_y = True
            elif abs(self.cat_velocity_y) < 0.1: # If velocity is near zero, consider Y target reached
                target_reached_y = True

            # If the cat hits any screen boundary during an edge run, or reaches its specific target
            # consider the run complete.
            hit_boundary = (new_x <= 0 or new_x >= max_x or new_y <= 0 or new_y >= max_y)

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
            if new_x < 0:
                new_x = 0.0 # Clamp to 0
                self.cat_velocity_x *= -1 # Reverse direction
                bounced = True
            elif new_x > max_x:
                new_x = float(max_x) # Clamp to max_x
                self.cat_velocity_x *= -1 # Reverse direction
                bounced = True

            # Vertical collision
            if new_y < 0:
                new_y = 0.0 # Clamp to 0
                self.cat_velocity_y *= -1 # Reverse direction
                bounced = True
            elif new_y > max_y:
                new_y = float(max_y) # Clamp to max_y
                self.cat_velocity_y *= -1 # Reverse direction
                bounced = True

            self.move(int(new_x), int(new_y)) # Apply new position to the window, casting to int

            # Update 'moving_right' flag for correct sprite flipping
            if self.cat_velocity_x > 0:
                self.moving_right = True
            elif self.cat_velocity_x < 0:
                self.moving_right = False

            # Adjust animation based on movement state
            if bounced and (abs(self.cat_velocity_x) > 0.1 or abs(self.cat_velocity_y) > 0.1):
                self._set_animation('Walk') # Cat should be walking after a bounce
            elif not bounced and abs(self.cat_velocity_x) < 0.1 and abs(self.cat_velocity_y) < 0.1 and self.current_animation != 'Idle':
                self._set_animation('Idle') # If stopped, go to idle
            elif not bounced and (abs(self.cat_velocity_x) > 0.1 or abs(self.cat_velocity_y) > 0.1) and self.current_animation != 'Walk':
                self._set_animation('Walk') # If moving, go to walk

    def _random_movement(self):
        """
        Randomly sets the cat's movement state (Idle, Walk, or Run to Edge).
        Determines new velocity for walking/running or stops movement for idling.
        """
        random_choice = random.random()

        # Ensure 'Run' animation sprites are available before attempting an edge run
        if 'Run' in self.sprites and self.sprites['Run']:
            if random_choice < 0.25: # 25% chance to run to an edge
                self._start_edge_run()
            elif random_choice < 0.8: # 55% chance to walk (0.25 to 0.8)
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
            else: # 20% chance to idle (0.8 to 1.0)
                self.cat_velocity_x = 0.0
                self.cat_velocity_y = 0.0
                self._set_animation('Idle')
        else: # Fallback if 'Run' sprites are not available, only allow Idle/Walk
            if random_choice < 0.6: # 60% chance to walk
                angle = random.uniform(0, 2 * math.pi)
                vx = MOVEMENT_SPEED * random.uniform(0.7, 1.3) * math.cos(angle)
                vy = MOVEMENT_SPEED * random.uniform(0.7, 1.3) * math.sin(angle)

                if abs(vx) < 0.1 and abs(vy) < 0.1:
                    if random.random() < 0.5:
                        vx = MOVEMENT_SPEED * random.choice([-1, 1])
                        vy = 0.0
                    else:
                        vx = 0.0
                        vy = MOVEMENT_SPEED * random.choice([-1, 1])

                self.cat_velocity_x = vx
                self.cat_velocity_y = vy
                self._set_animation('Walk')
            else: # 40% chance to idle
                self.cat_velocity_x = 0.0
                self.cat_velocity_y = 0.0
                self._set_animation('Idle')


    def _start_edge_run(self):
        """
        Initiates the 'run to edge' behavior.
        Calculates the velocity to move from the cat's current position
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

        # Calculate vector (dx, dy) from current position to target
        # The cat starts from its current self.x(), self.y()
        dx = float(target_x) - self.x()
        dy = float(target_y) - self.y()
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

    # --- Mouse Events for Dragging ---
    def mousePressEvent(self, event):
        """Handles mouse button press events for dragging the window."""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            # Calculate the offset from the window's top-left corner to the mouse click position
            self.offset = event.pos()
            # Stop random movement and set to Idle when dragging begins
            self.random_behavior_timer.stop() # Temporarily stop random movement changes
            self.cat_velocity_x = 0.0 # Stop current movement
            self.cat_velocity_y = 0.0
            self._set_animation('Idle') # Cat idles while being dragged
            # If it was in an edge run, also reset that state
            self.is_edge_running = False

    def mouseMoveEvent(self, event):
        """Handles mouse movement events while dragging the window."""
        if self.dragging:
            # Move the window based on the current mouse position relative to the initial click offset
            self.move(self.mapToGlobal(event.pos() - self.offset))

    def mouseReleaseEvent(self, event):
        """Handles mouse button release events after dragging."""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            # Restart random movement after dragging is finished
            self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)

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
            # When showing, restart random movement
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
        # Create a temporary QApplication to show message box before exiting
        temp_app = QApplication([])
        msg = MessageBox(f"Error: Default 'assets/cat' directory not found at '{initial_asset_check_dir}'.\n"
                         "Please ensure your sprite assets are correctly placed.", parent=None)
        msg.show()
        sys.exit(temp_app.exec_()) # Exit the application if default assets are missing

    # Initialize and show the main application window
    cat_app = CatCompanionApp()

    # Show an initial message box to the user from the tray icon
    # This message now appears via the tray icon's message bubble.
    cat_app.tray_icon.showMessage(
        "Desk Pet Companion Started",
        "The application is running in the system tray. Click the icon to show/hide your pet.",
        QSystemTrayIcon.Information,
        3000
    )

    sys.exit(app.exec_()) # Start the Qt event loop
