import sys
import os
import random
import math
from PyQt5.QtWidgets import (
    QApplication, QLabel, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QSystemTrayIcon, QMenu, QAction, QDesktopWidget, QStyle
)
from PyQt5.QtGui import QPixmap, QTransform, QIcon
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, pyqtSignal, QUrl, QSize
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

CAT_WIDTH = 120
CAT_HEIGHT = 120
ANIMATION_FRAME_RATE = 100
MOVEMENT_SPEED = 3
MOVEMENT_CHANGE_DELAY = 3000
RUN_SPEED_MULTIPLIER = 2.5
CLICK_THRESHOLD = 5
JUMP_INITIAL_VELOCITY = 15.0
GRAVITY = 0.8
DEAD_ANIMATION_THRESHOLD = 5
DEAD_ANIMATION_PAUSE_DURATION = 3000
FOOD_SIZE = 40

ANIMATION_FRAMES = {
    "Dead": 10, "Fall": 8, "Hurt": 10, "Idle": 10, "Jump": 8, "Run": 8, "Slide": 10, "Walk": 10
}

class ControlBox(QWidget):
    move_left_signal = pyqtSignal()
    move_right_signal = pyqtSignal()
    move_up_signal = pyqtSignal()
    move_down_signal = pyqtSignal()
    stop_movement_signal = pyqtSignal()
    jump_signal = pyqtSignal()
    slide_signal = pyqtSignal()
    closed_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pet Control")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setStyleSheet("""
            QWidget {
                background-color: #2e2e2e;
                border-radius: 10px;
                font-family: 'Inter', sans-serif;
                padding: 15px;
            }
            QPushButton {
                background-color: #555555;
                color: white;
                padding: 10px 15px;
                border-radius: 5px;
                border: none;
                font-weight: bold;
                min-width: 60px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton#stopButton {
                background-color: #ff6b6b;
            }
            QPushButton#stopButton:hover {
                background-color: #ff8c8c;
            }
            QPushButton#actionButton {
                background-color: #4CAF50;
            }
            QPushButton#actionButton:hover {
                background-color: #66BB6A;
            }
        """)
        self._init_ui()
        self.setFocusPolicy(Qt.StrongFocus)
        self._active_movement_keys = set()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        d_pad_layout = QVBoxLayout()

        top_row = QHBoxLayout()
        btn_up = QPushButton("Up")
        btn_up.pressed.connect(self.move_up_signal)
        btn_up.released.connect(self.stop_movement_signal)
        top_row.addStretch()
        top_row.addWidget(btn_up)
        top_row.addStretch()

        mid_row = QHBoxLayout()
        btn_left = QPushButton("Left")
        btn_left.pressed.connect(self.move_left_signal)
        btn_left.released.connect(self.stop_movement_signal)
        btn_stop = QPushButton("Stop")
        btn_stop.setObjectName("stopButton")
        btn_stop.clicked.connect(self.stop_movement_signal)
        btn_right = QPushButton("Right")
        btn_right.pressed.connect(self.move_right_signal)
        btn_right.released.connect(self.stop_movement_signal)
        mid_row.addWidget(btn_left)
        mid_row.addWidget(btn_stop)
        mid_row.addWidget(btn_right)

        bottom_row = QHBoxLayout()
        btn_down = QPushButton("Down")
        btn_down.pressed.connect(self.move_down_signal)
        btn_down.released.connect(self.stop_movement_signal)
        bottom_row.addStretch()
        bottom_row.addWidget(btn_down)
        bottom_row.addStretch()

        d_pad_layout.addLayout(top_row)
        d_pad_layout.addLayout(mid_row)
        d_pad_layout.addLayout(bottom_row)
        main_layout.addLayout(d_pad_layout)

        action_layout = QHBoxLayout()
        btn_jump = QPushButton("Jump")
        btn_jump.setObjectName("actionButton")
        btn_jump.clicked.connect(self.jump_signal)
        btn_slide = QPushButton("Slide")
        btn_slide.setObjectName("actionButton")
        btn_slide.clicked.connect(self.slide_signal)
        action_layout.addStretch()
        action_layout.addWidget(btn_jump)
        action_layout.addWidget(btn_slide)
        action_layout.addStretch()
        main_layout.addLayout(action_layout)

        self.setLayout(main_layout)
        self.adjustSize()

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            event.ignore()
            return

        key = event.key()
        if key == Qt.Key_A or key == Qt.Key_Left:
            self.move_left_signal.emit()
            self._active_movement_keys.add(Qt.Key_A)
        elif key == Qt.Key_D or key == Qt.Key_Right:
            self.move_right_signal.emit()
            self._active_movement_keys.add(Qt.Key_D)
        elif key == Qt.Key_W or key == Qt.Key_Up:
            self.move_up_signal.emit()
            self._active_movement_keys.add(Qt.Key_W)
        elif key == Qt.Key_S or key == Qt.Key_Down:
            self.move_down_signal.emit()
            self._active_movement_keys.add(Qt.Key_S)
        elif key == Qt.Key_Space:
            self.jump_signal.emit()
        elif key == Qt.Key_Shift:
            self.slide_signal.emit()
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            event.ignore()
            return

        key = event.key()
        if key == Qt.Key_A or key == Qt.Key_Left:
            if Qt.Key_A in self._active_movement_keys:
                self._active_movement_keys.remove(Qt.Key_A)
            if not self._active_movement_keys:
                self.stop_movement_signal.emit()
        elif key == Qt.Key_D or key == Qt.Key_Right:
            if Qt.Key_D in self._active_movement_keys:
                self._active_movement_keys.remove(Qt.Key_D)
            if not self._active_movement_keys:
                self.stop_movement_signal.emit()
        elif key == Qt.Key_W or key == Qt.Key_Up:
            if Qt.Key_W in self._active_movement_keys:
                self._active_movement_keys.remove(Qt.Key_W)
            if not self._active_movement_keys:
                self.stop_movement_signal.emit()
        elif key == Qt.Key_S or key == Qt.Key_Down:
            if Qt.Key_S in self._active_movement_keys:
                self._active_movement_keys.remove(Qt.Key_S)
            if not self._active_movement_keys:
                self.stop_movement_signal.emit()
        else:
            super().keyReleaseEvent(event)
            return
        event.accept()

    def closeEvent(self, event):
        self.closed_signal.emit()
        super().closeEvent(event)

class FoodItem(QLabel):
    food_removed = pyqtSignal(object)

    def __init__(self, image_path="", initial_pos=None): # Removed parent argument
        super().__init__() # Initialized without a parent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.BypassWindowManagerHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setScaledContents(True)

        self.original_pixmap = QPixmap(image_path)
        if not self.original_pixmap.isNull():
            self.setPixmap(self.original_pixmap.scaled(FOOD_SIZE, FOOD_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.resize(FOOD_SIZE, FOOD_SIZE)
        else:
            self.setText("Food")
            self.setStyleSheet("background-color: yellow; border-radius: 5px;")
            self.resize(FOOD_SIZE, FOOD_SIZE)

        if initial_pos:
            self.move(initial_pos)
        else:
            screen_rect = QApplication.desktop().screenGeometry()
            x = random.randint(0, screen_rect.width() - self.width())
            y = random.randint(0, screen_rect.height() - self.height())
            self.move(x, y)
        
        self.show()
        self.dragging = False
        self.offset = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()
            self.raise_()

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_pos = self.mapToGlobal(event.pos() - self.offset)
            screen_rect = QApplication.desktop().screenGeometry()
            
            x = max(0, min(new_pos.x(), screen_rect.width() - self.width()))
            y = max(0, min(new_pos.y(), screen_rect.height() - self.height()))
            self.move(x, y)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False


class CatCompanionApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desk Pet Companion")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(CAT_WIDTH, CAT_HEIGHT)

        self.cat_label = QLabel(self)
        self.cat_label.setGeometry(0, 0, CAT_WIDTH, CAT_HEIGHT)
        self.cat_label.setAlignment(Qt.AlignCenter)

        self.current_asset_type = 'cat'
        self.sprites = {}
        self.food_sprites = []
        self.active_food_items = []
        self.current_animation = 'Idle'
        self.current_frame_index = 0

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._next_frame)
        self.animation_timer.start(ANIMATION_FRAME_RATE)

        self._current_x = 0.0
        self._current_y = 0.0
        self.cat_velocity_x = 0.0
        self.cat_velocity_y = 0.0
        self.moving_right = True
        self.is_edge_running = False
        self.target_x = 0
        self.target_y = 0
        self.is_sliding = False
        self.slide_target_pos = QPoint()
        self._is_jumping = False
        self._is_manual_moving = False
        self._click_count = 0
        self.target_food_item = None

        self.movement_timer = QTimer(self)
        self.movement_timer.timeout.connect(self._update_cat_position)
        self.movement_timer.start(16)

        self.random_behavior_timer = QTimer(self)
        self.random_behavior_timer.timeout.connect(self._random_movement)

        self._dead_animation_cooldown_timer = QTimer(self)
        self._dead_animation_cooldown_timer.setSingleShot(True)
        self._dead_animation_cooldown_timer.timeout.connect(self._dead_animation_cooldown_finished)

        self.dragging = False
        self.offset = QPoint()
        self.mouse_press_pos = QPoint()
        self.is_playing_one_shot_animation = False

        self.control_box = None

        self.media_player = QMediaPlayer(self)
        self.audio_files = {} 
        self.audio_enabled = True
        self.audio_play_timer = QTimer(self)
        self.audio_play_timer.timeout.connect(self._play_random_audio)
        self.media_player.stateChanged.connect(self._audio_state_changed)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("Desk Pet Companion")
        tray_menu = QMenu()

        self.toggle_visibility_action = QAction("Hide Pet", self)
        self.toggle_visibility_action.triggered.connect(self.toggle_visibility)
        tray_menu.addAction(self.toggle_visibility_action)

        self.open_control_box_action = QAction("Open Control Box", self)
        self.open_control_box_action.triggered.connect(self._open_control_box)
        tray_menu.addAction(self.open_control_box_action)

        self.toggle_audio_action = QAction("Disable Audio", self)
        self.toggle_audio_action.triggered.connect(self._toggle_audio)
        tray_menu.addAction(self.toggle_audio_action)
        
        food_menu = QMenu("Food", self)
        add_random_food_action = QAction("Add Random Food", self)
        add_random_food_action.triggered.connect(self.add_random_food)
        food_menu.addAction(add_random_food_action)

        clear_all_food_action = QAction("Clear All Food", self)
        clear_all_food_action.triggered.connect(self.clear_all_food)
        food_menu.addAction(clear_all_food_action)
        tray_menu.addMenu(food_menu)

        tray_menu.addSeparator()

        pet_type_menu = QMenu("Change Pet Type", self)
        self.cat_action = QAction("Cat", self, checkable=True)
        self.dog_action = QAction("Dog", self, checkable=True)
        self.cat_action.triggered.connect(lambda: self.change_pet_type('cat'))
        self.dog_action.triggered.connect(lambda: self.change_pet_type('dog'))
        pet_type_menu.addAction(self.cat_action)
        pet_type_menu.addAction(self.dog_action)
        tray_menu.addMenu(pet_type_menu)

        tray_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        self.tray_icon_current_frame_index = 0
        self.tray_animation_timer = QTimer(self)
        self.tray_animation_timer.timeout.connect(self._update_tray_icon_animation)
        self.tray_animation_timer.start(ANIMATION_FRAME_RATE * 2)

        self.change_pet_type(self.current_asset_type)
        self._load_food_sprites()
        self._set_initial_position()
        self.show()

        self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)
        self.audio_play_timer.start(random.randint(5000, 15000))

    def _get_asset_path(self, animation_name, frame_number):
        base_dir = os.path.dirname(__file__)
        return os.path.join(base_dir, 'assets', self.current_asset_type, f'{animation_name} ({frame_number}).png')

    def _get_food_asset_path(self, food_file_name):
        base_dir = os.path.dirname(__file__)
        return os.path.join(base_dir, 'assets', 'food', food_file_name)

    def _load_sprites(self):
        all_sprites = {}
        asset_dir = os.path.join(os.path.dirname(__file__), 'assets', self.current_asset_type)
        if not os.path.exists(asset_dir) or not os.path.isdir(asset_dir):
            print(f"Error: Asset directory '{self.current_asset_type}' not found at '{asset_dir}'.\nPlease ensure your sprite assets are correctly placed.")
            return {}

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
    
    def _load_food_sprites(self):
        food_dir = os.path.join(os.path.dirname(__file__), 'assets', 'food')
        if not os.path.exists(food_dir) or not os.path.isdir(food_dir):
            print(f"Error: Food asset directory not found at '{food_dir}'.")
            return

        self.food_sprites = []
        for filename in os.listdir(food_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                self.food_sprites.append(self._get_food_asset_path(filename))
        
        if not self.food_sprites:
            print("Warning: No food sprites found in 'assets/food' folder.")

    def add_random_food(self):
        if not self.food_sprites:
            print("No food sprites available to add.")
            return
        
        food_path = random.choice(self.food_sprites)
        # Removed parent=self to make FoodItem a top-level window
        food_item = FoodItem(image_path=food_path) 
        food_item.food_removed.connect(self._on_food_removed)
        self.active_food_items.append(food_item)
        food_item.show()
        self.raise_()

    def _on_food_removed(self, food_item):
        if food_item in self.active_food_items:
            food_item.hide()
            food_item.deleteLater()
            self.active_food_items.remove(food_item)
            if self.target_food_item == food_item:
                self.target_food_item = None

    def clear_all_food(self):
        for food_item in list(self.active_food_items):
            food_item.hide()
            food_item.deleteLater()
        self.active_food_items.clear()
        self.target_food_item = None

    def _load_audio_file(self, pet_type):
        audio_path = os.path.join(os.path.dirname(__file__), 'assets', pet_type, 'audio.wav')
        if os.path.exists(audio_path):
            return QUrl.fromLocalFile(audio_path)
        else:
            print(f"Warning: Audio file not found for {pet_type} at {audio_path}")
            return None

    def change_pet_type(self, pet_type):
        if self.current_asset_type == 'cat':
            self.cat_action.setChecked(False)
        elif self.current_asset_type == 'dog':
            self.dog_action.setChecked(False)

        self.current_asset_type = pet_type
        self.sprites = self._load_sprites()
        self.audio_files[self.current_asset_type] = self._load_audio_file(self.current_asset_type)

        if self.sprites:
            self._set_animation('Idle')
            if self.current_asset_type == 'cat':
                self.cat_action.setChecked(True)
            elif self.current_asset_type == 'dog':
                self.dog_action.setChecked(True)
            self._update_tray_icon_animation()
        else:
            self.cat_label.setText(f"Error: No {pet_type} sprites found.")
            self.animation_timer.stop()
            self.movement_timer.stop()
            self.random_behavior_timer.stop()
            self.tray_animation_timer.stop()
            self._dead_animation_cooldown_timer.stop()
            if pet_type == 'dog':
                self.current_asset_type = 'cat'
                self.cat_action.setChecked(True)
                print(f"Failed to load 'dog' sprites. Reverted to 'cat'.")
        
        self.media_player.stop()
        if self.audio_enabled:
            self.audio_play_timer.start(random.randint(1000, 5000)) 

    def _set_initial_position(self):
        screen_rect = QApplication.desktop().screenGeometry()
        max_x = screen_rect.width() - self.width()
        max_y = screen_rect.height() - self.height()
        initial_x = random.randint(0, max_x)
        initial_y = random.randint(0, max_y)
        self._current_x = float(initial_x)
        self._current_y = float(initial_y)
        self.move(int(self._current_x), int(self._current_y))

    def _set_animation(self, new_animation_name):
        if self.is_playing_one_shot_animation and new_animation_name != self.current_animation:
            return
        if new_animation_name not in self.sprites or not self.sprites[new_animation_name]:
            print(f"Error: Animation '{new_animation_name}' not found or has no frames for {self.current_asset_type}. Falling back to Idle.")
            new_animation_name = 'Idle'
            if 'Idle' not in self.sprites or not self.sprites['Idle']:
                self.cat_label.setText(f"Error: No {self.current_asset_type} sprites loaded! Check assets folder.")
                self.animation_timer.stop()
                self.movement_timer.stop()
                self.random_behavior_timer.stop()
                self._dead_animation_cooldown_timer.stop()
                return
        if self.current_animation != new_animation_name:
            self.current_animation = new_animation_name
            self.current_frame_index = 0
            self._update_cat_pixmap()

    def _next_frame(self):
        sprites = self.sprites.get(self.current_animation)
        if sprites:
            if self.current_animation == 'Dead' and self.current_frame_index == len(sprites) - 1:
                self._update_cat_pixmap()
                return

            self.current_frame_index = (self.current_frame_index + 1) % len(sprites)
            self._update_cat_pixmap()
        else:
            self.cat_label.clear()

    def _update_cat_pixmap(self):
        sprites = self.sprites.get(self.current_animation)
        if sprites and self.current_frame_index < len(sprites):
            pixmap = sprites[self.current_frame_index]
            if not self.moving_right:
                pixmap = pixmap.transformed(QTransform().scale(-1, 1))
            self.cat_label.setPixmap(pixmap)
        else:
            self.cat_label.clear()

    def _update_cat_position(self):
        screen_rect = QApplication.desktop().screenGeometry()
        max_x = screen_rect.width() - self.width()
        ground_y = float(screen_rect.height() - self.height())

        if self._is_jumping:
            self.cat_velocity_y += GRAVITY
            self._current_y += self.cat_velocity_y
            if self._current_y >= ground_y:
                self._current_y = ground_y
                self.cat_velocity_y = 0.0
                self._is_jumping = False
                self.is_playing_one_shot_animation = False
                self._set_animation('Idle')
                if not self._is_manual_moving:
                    self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)
            self._current_x += self.cat_velocity_x
            self._current_x = max(0.0, min(self._current_x, float(max_x)))
            self.move(int(self._current_x), int(self._current_y))
            return

        if self.dragging or (self.is_playing_one_shot_animation and not self._is_jumping) or self._dead_animation_cooldown_timer.isActive():
            return

        if not self._is_manual_moving and not self.is_sliding and not self._is_jumping and not self.is_playing_one_shot_animation:
            if self.target_food_item and not self.target_food_item.isHidden():
                target_food_pos = self.target_food_item.pos()
                target_x = target_food_pos.x() + self.target_food_item.width() // 2
                target_y = target_food_pos.y() + self.target_food_item.height() // 2
                
                cat_center_x = self._current_x + CAT_WIDTH // 2
                cat_center_y = self._current_y + CAT_HEIGHT // 2

                dx = target_x - cat_center_x
                dy = target_y - cat_center_y
                distance = math.sqrt(dx*dx + dy*dy)

                if distance < (CAT_WIDTH / 2 + FOOD_SIZE / 2 - 10):
                    self.target_food_item.food_removed.emit(self.target_food_item)
                    self.target_food_item = None
                    self.cat_velocity_x = 0.0
                    self.cat_velocity_y = 0.0
                    self._set_animation('Idle')
                    if not self._is_manual_moving and not self._dead_animation_cooldown_timer.isActive() and not self.active_food_items:
                        self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)
                else:
                    self.random_behavior_timer.stop()
                    self.cat_velocity_x = (dx / distance) * MOVEMENT_SPEED * RUN_SPEED_MULTIPLIER
                    self.cat_velocity_y = (dy / distance) * MOVEMENT_SPEED * RUN_SPEED_MULTIPLIER
                    self._set_animation('Run')
            else:
                closest_food = None
                min_distance = float('inf')
                for food in self.active_food_items:
                    if not food.isHidden():
                        food_center = food.pos() + QPoint(food.width() // 2, food.height() // 2)
                        cat_center = QPoint(int(self._current_x) + CAT_WIDTH // 2, int(self._current_y) + CAT_HEIGHT // 2)
                        distance = math.sqrt((food_center.x() - cat_center.x())**2 + (food_center.y() - cat_center.y())**2)
                        if distance < min_distance:
                            min_distance = distance
                            closest_food = food
                self.target_food_item = closest_food
                if not self.target_food_item and not self.random_behavior_timer.isActive() and not self._is_manual_moving and not self._dead_animation_cooldown_timer.isActive():
                    self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)

        self._current_x += self.cat_velocity_x
        self._current_y += self.cat_velocity_y

        if self.is_sliding:
            target_reached_x = False
            if self.cat_velocity_x > 0 and self._current_x >= self.slide_target_pos.x():
                target_reached_x = True
            elif self.cat_velocity_x < 0 and self._current_x <= self.slide_target_pos.x():
                target_reached_x = True
            elif abs(self.cat_velocity_x) < 0.1:
                target_reached_x = True

            target_reached_y = False
            if self.cat_velocity_y > 0 and self._current_y >= self.slide_target_pos.y():
                target_reached_y = True
            elif self.cat_velocity_y < 0 and self._current_y <= self.slide_target_pos.y():
                target_reached_y = True
            elif abs(self.cat_velocity_y) < 0.1:
                target_reached_y = True

            if self.cat_velocity_y == 0:
                if target_reached_x:
                    self._current_x = float(self.slide_target_pos.x())
                    self.is_sliding = False
            else:
                if target_reached_x and target_reached_y:
                    self._current_x = float(self.slide_target_pos.x())
                    self._current_y = float(self.slide_target_pos.y())
                    self.is_sliding = False

            if not self.is_sliding:
                self.cat_velocity_x = 0.0
                self.cat_velocity_y = 0.0
                self._set_animation('Idle')
                if not self._is_manual_moving and not self.target_food_item:
                    self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)
            else:
                self._current_x = max(0.0, min(self._current_x, float(max_x)))
                self._current_y = max(0.0, min(self._current_y, ground_y))
                self.move(int(self._current_x), int(self._current_y))
                if self.cat_velocity_x > 0:
                    self.moving_right = True
                elif self.cat_velocity_x < 0:
                    self.moving_right = False
                self._set_animation('Slide')
        
        elif self.is_edge_running:
            self._current_x = max(0.0, min(self._current_x, float(max_x)))
            self._current_y = max(0.0, min(self._current_y, ground_y))
            self.move(int(self._current_x), int(self._current_y))

            target_reached_x = False
            if self.cat_velocity_x > 0 and self._current_x >= self.target_x:
                target_reached_x = True
            elif self.cat_velocity_x < 0 and self._current_x <= self.target_x:
                target_reached_x = True
            elif abs(self.cat_velocity_x) < 0.1:
                target_reached_x = True

            target_reached_y = False
            if self.cat_velocity_y > 0 and self._current_y >= self.target_y:
                target_reached_y = True
            elif self.cat_velocity_y < 0 and self._current_y <= self.target_y:
                target_reached_y = True
            elif abs(self.cat_velocity_y) < 0.1:
                target_reached_y = True

            hit_boundary = (self._current_x <= 0 or self._current_x >= max_x or self._current_y <= 0 or self._current_y >= ground_y)
            
            if (target_reached_x and target_reached_y) or hit_boundary:
                self.is_edge_running = False
                self.cat_velocity_x = 0.0
                self.cat_velocity_y = 0.0
                self._set_animation('Idle')
                if not self._is_manual_moving and not self.target_food_item and not self._dead_animation_cooldown_timer.isActive():
                    self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)
            else:
                if self.cat_velocity_x > 0:
                    self.moving_right = True
                elif self.cat_velocity_x < 0:
                    self.moving_right = False
                self._set_animation('Run')
        else:
            bounced = False
            if self._current_x < 0:
                self._current_x = 0.0
                if not self._is_manual_moving and not self.target_food_item: self.cat_velocity_x *= -1
                bounced = True
            elif self._current_x > max_x:
                self._current_x = float(max_x)
                if not self._is_manual_moving and not self.target_food_item: self.cat_velocity_x *= -1
                bounced = True

            if self._current_y < 0:
                self._current_y = 0.0
                if not self._is_manual_moving and not self.target_food_item: self.cat_velocity_y *= -1
                bounced = True
            elif self._current_y > ground_y:
                self._current_y = ground_y
                if not self._is_manual_moving and not self.target_food_item: self.cat_velocity_y *= -1
                bounced = True

            self.move(int(self._current_x), int(self._current_y))

            if self.cat_velocity_x > 0:
                self.moving_right = True
            elif self.cat_velocity_x < 0:
                self.moving_right = False

            if not self.is_playing_one_shot_animation and not self._is_manual_moving and not self.target_food_item:
                if bounced and (abs(self.cat_velocity_x) > 0.1 or abs(self.cat_velocity_y) > 0.1):
                    self._set_animation('Walk')
                elif not bounced and abs(self.cat_velocity_x) < 0.1 and abs(self.cat_velocity_y) < 0.1 and self.current_animation != 'Idle':
                    self._set_animation('Idle')
                elif not bounced and (abs(self.cat_velocity_x) > 0.1 or abs(self.cat_velocity_y) > 0.1) and self.current_animation != 'Walk':
                    self._set_animation('Walk')
            elif self._is_manual_moving:
                if abs(self.cat_velocity_x) > 0.1 or abs(self.cat_velocity_y) > 0.1:
                    self._set_animation('Walk')
                else:
                    self._set_animation('Idle')


    def _random_movement(self):
        if self.is_playing_one_shot_animation or self.is_sliding or self._is_manual_moving or self._dead_animation_cooldown_timer.isActive() or self.target_food_item:
            return

        random_choice = random.random()
        if 'Run' in self.sprites and self.sprites['Run'] and random_choice < 0.15:
            self._start_edge_run()
        elif 'Slide' in self.sprites and self.sprites['Slide'] and random_choice < 0.30:
            self._start_slide_behavior()
        elif 'Jump' in self.sprites and self.sprites['Jump'] and random_choice < 0.40:
            self._play_one_shot_animation('Jump')
        elif random_choice < 0.80:
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
        else:
            self.cat_velocity_x = 0.0
            self.cat_velocity_y = 0.0
            self._set_animation('Idle')

    def _start_edge_run(self):
        screen_rect = QApplication.desktop().screenGeometry()
        screen_width = screen_rect.width()
        screen_height = screen_rect.height()

        edges = ['top', 'bottom', 'left', 'right']
        end_edge = random.choice(edges)

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

        dx = float(target_x) - self._current_x
        dy = float(target_y) - self._current_y
        distance = math.sqrt(dx*dx + dy*dy)

        if distance < 1.0:
            self.cat_velocity_x = 0.0
            self.cat_velocity_y = 0.0
            self.is_edge_running = False
            self._set_animation('Idle')
            return

        self.cat_velocity_x = (dx / distance) * MOVEMENT_SPEED * RUN_SPEED_MULTIPLIER
        self.cat_velocity_y = (dy / distance) * MOVEMENT_SPEED * RUN_SPEED_MULTIPLIER
        
        self.is_edge_running = True
        self.target_x = target_x
        self.target_y = target_y
        self._set_animation('Run')

        if self.cat_velocity_x > 0:
            self.moving_right = True
        elif self.cat_velocity_x < 0:
            self.moving_right = False

    def _start_slide_behavior(self):
        screen_rect = QApplication.desktop().screenGeometry()
        screen_width = screen_rect.width()
        screen_height = screen_rect.height()

        slide_type = random.choice(['horizontal', 'diagonal_down'])
        target_x, target_y = 0, 0

        if slide_type == 'horizontal':
            target_y = int(self._current_y)
            valid_x_targets = []
            if int(self._current_x + 50) < screen_width - CAT_WIDTH:
                valid_x_targets.extend(range(int(self._current_x + 50), screen_width - CAT_WIDTH + 1))
            if int(self._current_x - 50) >= 0:
                valid_x_targets.extend(range(0, int(self._current_x - 50) + 1))

            if not valid_x_targets:
                target_x = int(self._current_x)
            else:
                target_x = random.choice(valid_x_targets)

        elif slide_type == 'diagonal_down':
            min_target_y = int(self._current_y + 50)
            target_y = random.randint(min_target_y, screen_height - CAT_HEIGHT) if min_target_y <= screen_height - CAT_HEIGHT else int(self._current_y)

            valid_x_targets = []
            if int(self._current_x + 10) < screen_width - CAT_WIDTH:
                valid_x_targets.extend(range(int(self._current_x + 10), screen_width - CAT_WIDTH + 1))
            if int(self._current_x - 10) >= 0:
                valid_x_targets.extend(range(0, int(self._current_x - 10) + 1))

            if not valid_x_targets:
                target_x = int(self._current_x)
            else:
                target_x = random.choice(valid_x_targets)

        dx = float(target_x) - self._current_x
        dy = float(target_y) - self._current_y
        distance = math.sqrt(dx*dx + dy*dy)

        if distance < 1.0:
            self.cat_velocity_x = 0.0
            self.cat_velocity_y = 0.0
            self.is_sliding = False
            self._set_animation('Idle')
            return

        slide_speed = MOVEMENT_SPEED * 1.5
        self.cat_velocity_x = (dx / distance) * slide_speed
        self.cat_velocity_y = (dy / distance) * slide_speed

        self.is_sliding = True
        self.slide_target_pos = QPoint(target_x, target_y)
        self._set_animation('Slide')

        if self.cat_velocity_x > 0:
            self.moving_right = True
        elif self.cat_velocity_x < 0:
            self.moving_right = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.mouse_press_pos = event.globalPos()
            self.offset = event.pos()
            self.random_behavior_timer.stop()
            self._dead_animation_cooldown_timer.stop()
            self._is_manual_moving = False
            self.cat_velocity_x = 0.0
            self.cat_velocity_y = 0.0
            self._set_animation('Idle')
            self.is_edge_running = False
            self.is_sliding = False
            self._is_jumping = False
            self.media_player.stop() 
            self.target_food_item = None

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(self.mapToGlobal(event.pos() - self.offset))
            global_pos = self.mapToGlobal(event.pos() - self.offset)
            self._current_x = float(global_pos.x())
            self._current_y = float(global_pos.y())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            mouse_release_pos = event.globalPos()
            distance_moved = (mouse_release_pos - self.mouse_press_pos).manhattanLength()

            if distance_moved < CLICK_THRESHOLD:
                self._click_count += 1
                if self._click_count >= DEAD_ANIMATION_THRESHOLD:
                    self._play_dead_animation()
                    self._click_count = 0
                else:
                    self._play_one_shot_animation('Hurt')
            else:
                if not self._is_manual_moving and not self._dead_animation_cooldown_timer.isActive() and not self.active_food_items:
                    self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)
            
            if self.audio_enabled and self.media_player.state() == QMediaPlayer.StoppedState and not self._dead_animation_cooldown_timer.isActive():
                self.audio_play_timer.start(random.randint(1000, 5000)) 
        
        if not self.dragging and not self.target_food_item and self.active_food_items:
            self.target_food_item = self.active_food_items[0] if self.active_food_items else None
            if self.target_food_item:
                self.random_behavior_timer.stop()
                self.is_edge_running = False
                self.is_sliding = False
                self._is_manual_moving = False

    def _play_one_shot_animation(self, animation_name):
        if animation_name not in self.sprites or not self.sprites[animation_name]:
            print(f"Warning: Cannot play one-shot animation '{animation_name}'. Sprites not found.")
            self.is_playing_one_shot_animation = False
            if not self._is_manual_moving and not self._dead_animation_cooldown_timer.isActive() and not self.target_food_item:
                self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)
            return

        self.is_playing_one_shot_animation = True
        self.random_behavior_timer.stop()
        self._is_manual_moving = False
        self.cat_velocity_x = 0.0
        self.media_player.stop() 

        if animation_name == 'Jump':
            self.cat_velocity_y = -JUMP_INITIAL_VELOCITY
            self._is_jumping = True
        else:
            self.cat_velocity_y = 0.0
            duration_ms = len(self.sprites[animation_name]) * ANIMATION_FRAME_RATE
            QTimer.singleShot(duration_ms, self._one_shot_animation_finished)
        
        self.current_animation = animation_name
        self.current_frame_index = 0
        self._update_cat_pixmap()

    def _one_shot_animation_finished(self):
        if self.current_animation == 'Dead':
            self._dead_animation_cooldown_timer.start(DEAD_ANIMATION_PAUSE_DURATION)
            return
            
        self.is_playing_one_shot_animation = False
        self._set_animation('Idle')
        if not self._is_manual_moving and not self.target_food_item:
            self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)
        if self.audio_enabled and self.media_player.state() == QMediaPlayer.StoppedState:
            self.audio_play_timer.start(random.randint(1000, 5000))

    def _play_dead_animation(self):
        if 'Dead' not in self.sprites or not self.sprites['Dead']:
            print("Warning: Cannot play 'Dead' animation. Sprites not found. Reverting to Hurt.")
            self._play_one_shot_animation('Hurt')
            return

        self.is_playing_one_shot_animation = True
        self.random_behavior_timer.stop()
        self.movement_timer.stop()
        self.audio_play_timer.stop()
        self.media_player.stop()
        self.target_food_item = None

        self._is_manual_moving = False
        self.is_edge_running = False
        self.is_sliding = False
        self._is_jumping = False
        self.cat_velocity_x = 0.0
        self.cat_velocity_y = 0.0

        self.current_animation = 'Dead'
        self.current_frame_index = 0
        self._update_cat_pixmap()
        
        duration_to_last_frame = (len(self.sprites['Dead']) - 1) * ANIMATION_FRAME_RATE
        QTimer.singleShot(duration_to_last_frame, self._reached_last_dead_frame)

    def _reached_last_dead_frame(self):
        if 'Dead' in self.sprites and self.sprites['Dead']:
            self.current_frame_index = len(self.sprites['Dead']) - 1
            self._update_cat_pixmap()
        self.animation_timer.stop()
        self._dead_animation_cooldown_timer.start(DEAD_ANIMATION_PAUSE_DURATION)

    def _dead_animation_cooldown_finished(self):
        self.is_playing_one_shot_animation = False
        self.animation_timer.start(ANIMATION_FRAME_RATE)
        self.movement_timer.start(16)

        self._set_animation('Idle')
        if not self._is_manual_moving and not self.target_food_item:
            self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)
        if self.audio_enabled:
            self.audio_play_timer.start(random.randint(1000, 5000))

    def _open_control_box(self):
        if self.control_box is None:
            self.control_box = ControlBox(self)
            self.control_box.move_left_signal.connect(self.start_manual_move_left)
            self.control_box.move_right_signal.connect(self.start_manual_move_right)
            self.control_box.move_up_signal.connect(self.start_manual_move_up)
            self.control_box.move_down_signal.connect(self.start_manual_move_down)
            self.control_box.stop_movement_signal.connect(self.stop_manual_movement)
            self.control_box.jump_signal.connect(self._manual_jump)
            self.control_box.slide_signal.connect(self._manual_slide)
            self.control_box.closed_signal.connect(self._on_control_box_closed)
            self.control_box.show()
            self.control_box.activateWindow()
            self.control_box.raise_()
        else:
            self.control_box.activateWindow()
            self.control_box.raise_()
        
        self.random_behavior_timer.stop()
        self.is_edge_running = False
        self.is_sliding = False
        self._is_jumping = False
        self._is_manual_moving = True
        self.cat_velocity_x = 0.0
        self.cat_velocity_y = 0.0
        self._set_animation('Idle')
        self.media_player.stop() 
        self.audio_play_timer.stop() 
        self._dead_animation_cooldown_timer.stop()
        self.target_food_item = None

    def _on_control_box_closed(self):
        self.control_box = None
        self._is_manual_moving = False
        if not self.is_playing_one_shot_animation and not self._dead_animation_cooldown_timer.isActive() and not self.active_food_items:
            self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)
        self.cat_velocity_x = 0.0
        self.cat_velocity_y = 0.0
        self._set_animation('Idle')
        if self.audio_enabled and not self._dead_animation_cooldown_timer.isActive(): 
            self.audio_play_timer.start(random.randint(1000, 5000))

    def _start_manual_movement(self, vx, vy):
        if self._is_jumping or self.is_sliding or self._dead_animation_cooldown_timer.isActive():
            return
        self._is_manual_moving = True
        self.random_behavior_timer.stop()
        self.is_edge_running = False
        self.cat_velocity_x = vx
        self.cat_velocity_y = vy
        if abs(vx) > 0.1 or abs(vy) > 0.1:
            self._set_animation('Walk')
        else:
            self._set_animation('Idle')
        self.media_player.stop() 
        self.audio_play_timer.stop()
        self.target_food_item = None

    def start_manual_move_left(self):
        self.moving_right = False
        self._start_manual_movement(-MOVEMENT_SPEED, 0.0)

    def start_manual_move_right(self):
        self.moving_right = True
        self._start_manual_movement(MOVEMENT_SPEED, 0.0)

    def start_manual_move_up(self):
        self._start_manual_movement(0.0, -MOVEMENT_SPEED)

    def start_manual_move_down(self):
        self._start_manual_movement(0.0, MOVEMENT_SPEED)

    def stop_manual_movement(self):
        if not self._is_jumping and not self.is_sliding and not self._dead_animation_cooldown_timer.isActive():
            self.cat_velocity_x = 0.0
            self.cat_velocity_y = 0.0
            self._set_animation('Idle')
        if self.audio_enabled and self.media_player.state() == QMediaPlayer.StoppedState and not self._dead_animation_cooldown_timer.isActive():
            self.audio_play_timer.start(random.randint(1000, 5000))

    def _manual_jump(self):
        if not self._is_jumping and not self.is_playing_one_shot_animation and not self._dead_animation_cooldown_timer.isActive():
            self.stop_manual_movement()
            self._play_one_shot_animation('Jump')

    def _manual_slide(self):
        if not self.is_sliding and not self.is_playing_one_shot_animation and not self._dead_animation_cooldown_timer.isActive():
            self.stop_manual_movement()
            self._start_slide_behavior()

    def _update_tray_icon_animation(self):
        idle_sprites = self.sprites.get('Idle')
        if idle_sprites and len(idle_sprites) > 0:
            self.tray_icon_current_frame_index = (self.tray_icon_current_frame_index + 1) % len(idle_sprites)
            pixmap = idle_sprites[self.tray_icon_current_frame_index]
            self.tray_icon.setIcon(QIcon(pixmap))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))


    def _play_random_audio(self):
        if not self.audio_enabled or self._dead_animation_cooldown_timer.isActive():
            return
        audio_url = self.audio_files.get(self.current_asset_type)
        if audio_url and not audio_url.isEmpty():
            self.media_player.setMedia(QMediaContent(audio_url))
            self.media_player.play()
        else:
            print(f"No audio file found for {self.current_asset_type} or URL is empty.")
        self.audio_play_timer.start(random.randint(5000, 15000))

    def _audio_state_changed(self, state):
        if state == QMediaPlayer.StoppedState and self.audio_enabled and not self._is_manual_moving and not self.is_playing_one_shot_animation and not self._dead_animation_cooldown_timer.isActive():
            self.audio_play_timer.start(random.randint(1000, 5000))

    def _toggle_audio(self):
        self.audio_enabled = not self.audio_enabled
        if self.audio_enabled:
            self.toggle_audio_action.setText("Disable Audio")
            if self.media_player.state() == QMediaPlayer.StoppedState and not self._dead_animation_cooldown_timer.isActive(): 
                self.audio_play_timer.start(random.randint(1000, 5000)) 
        else:
            self.toggle_audio_action.setText("Enable Audio")
            self.media_player.stop()
            self.audio_play_timer.stop()

    def closeEvent(self, event):
        if self.control_box:
            self.control_box.close()
        self.media_player.stop() 
        self.audio_play_timer.stop()
        self._dead_animation_cooldown_timer.stop()
        self.clear_all_food()
        if QApplication.quitOnLastWindowClosed():
            self.tray_icon.hide()
            event.accept()
        else:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Desk Pet Companion",
                "The application is still running in the system tray. Click the icon to show/hide or exit.",
                QSystemTrayIcon.Information,
                2000
            )

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
            self.toggle_visibility_action.setText("Show Pet")
        else:
            self.show()
            self.toggle_visibility_action.setText("Hide Pet")
            if not self._is_manual_moving and not self._dead_animation_cooldown_timer.isActive():
                self.random_behavior_timer.start(MOVEMENT_CHANGE_DELAY)

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_visibility()

if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    base_dir = os.path.dirname(__file__)
    initial_asset_check_dir = os.path.join(base_dir, 'assets', 'cat')
    food_asset_check_dir = os.path.join(base_dir, 'assets', 'food')

    if not os.path.exists(initial_asset_check_dir) or not os.path.isdir(initial_asset_check_dir):
        print(f"Error: Default 'assets/cat' directory not found at '{initial_asset_check_dir}'.\nPlease ensure your sprite assets are correctly placed.")
        sys.exit(1)
    
    if not os.path.exists(food_asset_check_dir) or not os.path.isdir(food_asset_check_dir):
        print(f"Warning: 'assets/food' directory not found at '{food_asset_check_dir}'.\nFood functionality will be limited or unavailable.")

    cat_app = CatCompanionApp()
    cat_app.tray_icon.showMessage(
        "Desk Pet Companion Started",
        "The application is running in the system tray. Click the icon to show/hide your pet.",
        QSystemTrayIcon.Information,
        3000
    )
    sys.exit(app.exec_())
