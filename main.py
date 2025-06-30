import sys
import os
import random
import math
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QPushButton, QVBoxLayout, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QPixmap, QTransform, QIcon, QPainter
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect

# --- Configuration ---
PET_WIDTH = 120
PET_HEIGHT = 120

ANIMATION_FRAME_RATE = 100
MOVEMENT_SPEED = 3
MOVEMENT_CHANGE_DELAY = 3000

RUN_SPEED_MULTIPLIER = 2.5
DEAD_PAUSE_DURATION = 3000 # 3 seconds pause after dead animation finishes

# --- Sprite Assets Mapping ---
ANIMATION_FRAMES = {
    "Dead": 10, "Fall": 8, "Hurt": 10, "Idle": 10, "Jump": 8, "Run": 8, "Slide": 10, "Walk": 10
}

# --- Utility Function for Message Box (replacing alert()) ---
class MessageBox(QWidget):
    def __init__(self, message):
        super().__init__()
        self.setWindowTitle("Information")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 0.95); border-radius: 10px; padding: 20px;
                font-family: 'Inter', sans-serif; font-size: 14px; color: #eee; border: 1px solid #444;
            }
            QLabel { color: #eee; margin-bottom: 10px; }
            QPushButton {
                background-color: #007bff; color: white; border: none; padding: 8px 16px;
                border-radius: 5px; margin-top: 10px; font-weight: bold;
            }
            QPushButton:hover { background-color: #0056b3; }
        """)
        layout = QVBoxLayout(self)
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.message_label)
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.close)
        layout.addWidget(self.ok_button)
        self.adjustSize()
        screen_rect = QApplication.desktop().screenGeometry()
        self.move(screen_rect.center() - self.rect().center())

class PetCompanionApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop Pet Companion")
        self.asset_type = 'cat'
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(PET_WIDTH, PET_HEIGHT)

        self.pet_label = QLabel(self)
        self.pet_label.setGeometry(0, 0, PET_WIDTH, PET_HEIGHT)
        self.pet_label.setAlignment(Qt.AlignCenter)

        self.click_count = 0
        self.clicks_until_dead = random.randint(5, 9)
        self.is_reacting_to_click = False
        self.drag_start_position = QPoint()

        self.sprites = self._load_sprites()
        self.current_animation = 'Idle'
        self.current_frame_index = 0

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._next_frame)
        self.animation_timer.start(ANIMATION_FRAME_RATE)

        self.pet_velocity_x, self.pet_velocity_y = 0.0, 0.0
        self.moving_right = True
        self.is_edge_running = False
        self.target_x, self.target_y = 0, 0

        self.movement_timer = QTimer(self)
        self.movement_timer.timeout.connect(self._update_pet_position)
        self.movement_timer.start(16)

        self.random_behavior_timer = QTimer(self)
        self.random_behavior_timer.timeout.connect(self._random_movement)
        self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)

        self.dragging = False
        self.offset = QPoint()

        self._set_initial_position()
        self._setup_tray_icon()
        self._set_animation('Idle')

    def _get_asset_path(self, animation_name, frame_number):
        base_dir = os.path.dirname(__file__)
        return os.path.join(base_dir, 'assets', self.asset_type, f'{animation_name} ({frame_number}).png')

    def _load_sprites(self):
        all_sprites = {}
        for anim_name, num_frames in ANIMATION_FRAMES.items():
            all_sprites[anim_name] = []
            for i in range(1, num_frames + 1):
                path = self._get_asset_path(anim_name, i)
                try:
                    pixmap = QPixmap(path)
                    if not pixmap.isNull():
                        all_sprites[anim_name].append(pixmap.scaled(
                            PET_WIDTH, PET_HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation
                        ))
                    else:
                        print(f"Warning: Could not load sprite from {path}")
                except Exception as e:
                    print(f"Error loading {path}: {e}")
        return all_sprites

    def _setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self._update_tray_icon()
        self.tray_icon.setToolTip("Desktop Pet Companion")
        tray_menu = QMenu()
        change_character_menu = QMenu("Change Character", self)
        cat_action = QAction("Cat", self)
        cat_action.triggered.connect(lambda: self.change_character('cat'))
        change_character_menu.addAction(cat_action)
        dog_action = QAction("Dog", self)
        dog_action.triggered.connect(lambda: self.change_character('dog'))
        change_character_menu.addAction(dog_action)
        tray_menu.addMenu(change_character_menu)
        tray_menu.addSeparator()
        show_hide_action = QAction("Show/Hide", self)
        show_hide_action.triggered.connect(self.toggle_visibility)
        tray_menu.addAction(show_hide_action)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close_application)
        tray_menu.addAction(exit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def _update_tray_icon(self):
        icon_path = self._get_asset_path('Idle', 1)
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            print(f"Warning: Tray icon not found at {icon_path}")
            self.tray_icon.setIcon(QIcon())

    def change_character(self, new_type):
        if self.asset_type == new_type: return
        asset_dir = os.path.join(os.path.dirname(__file__), 'assets', new_type)
        if not os.path.exists(asset_dir) or not os.path.isdir(asset_dir):
            MessageBox(f"Error: Asset directory 'assets/{new_type}' not found.").show()
            return
        self.asset_type = new_type
        self.sprites = self._load_sprites()
        self._revive_pet() # Reset state completely on character change
        self._update_tray_icon()

    def _set_initial_position(self):
        screen_rect = QApplication.desktop().screenGeometry()
        self.move(random.randint(0, screen_rect.width() - self.width()),
                  random.randint(0, screen_rect.height() - self.height()))

    def _set_animation(self, new_animation_name):
        # Prevent animation changes if currently dead and not transitioning to 'Dead'
        if self.current_animation == 'Dead' and new_animation_name != 'Dead':
            return

        if new_animation_name not in self.sprites or not self.sprites[new_animation_name]:
            print(f"Error: Animation '{new_animation_name}' not found for '{self.asset_type}'. Falling back to Idle.")
            new_animation_name = 'Idle'
            if 'Idle' not in self.sprites or not self.sprites['Idle']:
                self.pet_label.setText(f"Error: No sprites for '{self.asset_type}'!")
                self.animation_timer.stop()
                return

        # Only change if it's a different animation
        if self.current_animation != new_animation_name:
            self.current_animation = new_animation_name
            self.current_frame_index = 0 # Reset frame index when changing animation
            self._update_pet_pixmap() # Immediately update to the first frame of the new animation
            # Ensure the animation timer is running when setting a new animation
            if not self.animation_timer.isActive():
                self.animation_timer.start(ANIMATION_FRAME_RATE)
        # If setting to the same animation, but the timer was stopped (e.g., after 'Dead'), restart it.
        elif not self.animation_timer.isActive():
             self.animation_timer.start(ANIMATION_FRAME_RATE)


    def _next_frame(self):
        sprites = self.sprites.get(self.current_animation)
        if sprites:
            if self.current_animation == 'Dead':
                # Always show the last frame if the animation is 'Dead'
                self.current_frame_index = len(sprites) - 1
            else:
                self.current_frame_index = (self.current_frame_index + 1) % len(sprites)
            self._update_pet_pixmap()

    def _update_pet_pixmap(self):
        sprites = self.sprites.get(self.current_animation)
        if sprites and self.current_frame_index < len(sprites):
            pixmap = sprites[self.current_frame_index]
            if not self.moving_right:
                pixmap = pixmap.transformed(QTransform().scale(-1, 1))
            self.pet_label.setPixmap(pixmap)
        else:
            self.pet_label.clear()

    def _update_pet_position(self):
        # Stop movement if reacting to click (including being dead) or being dragged
        if self.dragging or self.is_reacting_to_click:
            return

        current_x, current_y = self.x(), self.y()
        new_x, new_y = current_x + self.pet_velocity_x, current_y + self.pet_velocity_y
        screen_rect = QApplication.desktop().screenGeometry()
        max_x, max_y = screen_rect.width() - self.width(), screen_rect.height() - self.height()

        if new_x < 0: new_x, self.pet_velocity_x = 0.0, -self.pet_velocity_x
        elif new_x > max_x: new_x, self.pet_velocity_x = float(max_x), -self.pet_velocity_x
        if new_y < 0: new_y, self.pet_velocity_y = 0.0, -self.pet_velocity_y
        elif new_y > max_y: new_y, self.pet_velocity_y = float(max_y), -self.pet_velocity_y

        self.move(int(new_x), int(new_y))

        if self.pet_velocity_x > 0: self.moving_right = True
        elif self.pet_velocity_x < 0: self.moving_right = False

        is_moving = abs(self.pet_velocity_x) > 0.1 or abs(self.pet_velocity_y) > 0.1
        
        # Only change animation if not currently "Dead" or "Hurt"
        if not self.is_reacting_to_click:
            if is_moving and self.current_animation != 'Walk':
                self._set_animation('Walk')
            elif not is_moving and self.current_animation != 'Idle':
                self._set_animation('Idle')

    def _random_movement(self):
        # Stop random movement if reacting to click (including being dead) or being dragged
        if self.dragging or self.is_reacting_to_click:
            return

        random_choice = random.random()
        if random_choice < 0.8:
            angle = random.uniform(0, 2 * math.pi)
            self.pet_velocity_x = MOVEMENT_SPEED * math.cos(angle)
            self.pet_velocity_y = MOVEMENT_SPEED * math.sin(angle)
            self._set_animation('Walk')
        else:
            self.pet_velocity_x, self.pet_velocity_y = 0.0, 0.0
            self._set_animation('Idle')

    def _revive_pet(self):
        """Resets the pet's state after the 'Dead' animation and pause."""
        self.click_count = 0
        self.clicks_until_dead = random.randint(5, 9)
        self.is_reacting_to_click = False # Allow interactions and movement again
        
        # Explicitly set to 'Idle' to ensure animation state is reset and timer restarts
        self._set_animation('Idle') 
        
        # Restart timers for normal behavior
        self.movement_timer.start(16)
        self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)

    def _recover_from_hurt(self):
        """Resets the pet's state after the 'Hurt' animation."""
        self.is_reacting_to_click = False
        self._set_animation('Idle')
        self.movement_timer.start(16)
        self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)

    def mousePressEvent(self, event):
        close_button_rect = QRect(self.width() - 20, 0, 20, 20)
        if close_button_rect.contains(event.pos()):
            self.hide()
            return
        if event.button() == Qt.LeftButton:
            # Prevent new interactions if already reacting to a click (hurt/dead)
            if self.is_reacting_to_click: return
            
            self.dragging = True
            self.offset = event.pos()
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(self.mapToGlobal(event.pos() - self.offset))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Distinguish between a click and a drag
            is_drag = (event.pos() - self.drag_start_position).manhattanLength() > 3
            self.dragging = False

            if not is_drag and not self.is_reacting_to_click:
                self.is_reacting_to_click = True
                self.random_behavior_timer.stop() # Stop random movement
                self.movement_timer.stop() # Stop continuous movement
                self.pet_velocity_x, self.pet_velocity_y = 0.0, 0.0 # Stop pet instantly
                
                self.click_count += 1

                if self.click_count >= self.clicks_until_dead:
                    # --- Dead Logic ---
                    self._set_animation('Dead')
                    # Schedule revival after the dead animation duration + the pause duration
                    # We don't stop the animation timer, so the 'dead' animation continues to
                    # loop on its last frame.
                    dead_anim_play_time = ANIMATION_FRAME_RATE * len(self.sprites.get('Dead', [1]))
                    QTimer.singleShot(dead_anim_play_time + DEAD_PAUSE_DURATION, self._revive_pet)
                else:
                    # --- Hurt Logic ---
                    self._set_animation('Hurt')
                    hurt_anim_duration = ANIMATION_FRAME_RATE * len(self.sprites.get('Hurt', [1]))
                    QTimer.singleShot(hurt_anim_duration, self._recover_from_hurt)
            elif is_drag and not self.is_reacting_to_click:
                # If it was a drag and not reacting, restart random behavior timer
                self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)

    def closeEvent(self, event):
        self.hide()
        event.ignore()

    def toggle_visibility(self):
        self.setVisible(not self.isVisible())

    def close_application(self):
        self.tray_icon.hide()
        QApplication.quit()

if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    base_dir = os.path.dirname(__file__)
    cat_assets_dir = os.path.join(base_dir, 'assets', 'cat')
    if not os.path.exists(cat_assets_dir) or not os.path.isdir(cat_assets_dir):
        msg = MessageBox(f"Error: Default 'assets/cat' directory not found.")
        msg.show()
        sys.exit(app.exec_())

    pet_app = PetCompanionApp()
    pet_app.show()

    initial_message_box = MessageBox("Click your pet to interact!\nRight-click the tray icon to exit.")
    initial_message_box.show()

    sys.exit(app.exec_())