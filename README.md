# Compapet - Desk Pet Companion

![](https://github.com/user-attachments/assets/b3afd11d-383a-487b-b9a0-385e3ecc2a10)

This is a fun desktop companion application that brings a virtual pet (cat or dog) to your screen. The pet roams around your desktop, performs various animations, and can even chase after food items you place. It also, occasionally, leaves little "surprises" on your screen! You can control the pet's basic movements, toggle audio, and manage food and poop items through a control box or the system tray icon.

## Features

* **Desktop Pet:** A virtual pet that lives on your desktop.
* **Animations:** The pet performs various animations like Idle, Walk, Run, Jump, Slide, Hurt, and even a "Dead" animation if clicked too many times.
* **Random Behavior:** The pet moves randomly around the screen and performs actions autonomously.
* **Manual Control:** A control box allows you to manually move the pet (Up, Down, Left, Right), make it Jump, or Slide.
* **Food Interaction:** You can add food items to the desktop, and your pet will chase and "eat" them. Food items are draggable.
* **Poop Functionality:** Your pet will randomly leave poop items on your desktop. Clicking on a poop item will clear it.
* **System Tray Integration:** Control the pet's visibility, open the control box, toggle audio, add/clear food, add/clear poop, change pet type, and revive the pet from the system tray menu.
* **Pet Type Selection:** Choose between a cat or a dog companion.
* **Audio Feedback:** The pet makes sounds at random intervals (can be disabled).
* **Revive Option:** If the pet "dies" from too many clicks, you can revive it from the system tray.

## Installation

1.  **Prerequisites:**
    * Python 3.x installed on your system.
    * `PyQt5` library. You can install it using pip:
        ```bash
        pip install PyQt5 PyQt5-Qt5 PyQt5-sip
        ```

2.  **Download Assets:**
    Ensure you have the `assets` folder in the same directory as your `main.py` file. The `assets` folder should have the following structure:

    ```
    assets/
    ├── cat/
    │   ├── Dead (1).png
    │   ├── ... (other cat animation frames)
    │   └── audio.wav
    ├── dog/
    │   ├── Dead (1).png
    │   ├── ... (other dog animation frames)
    │   └── audio.wav
    ├── food/
    │   ├── food (1).png
    │   ├── ... (other food frames)
    └── poop/
        ├── poop (1).png
        ├── poop (2).png
        └── ... (other poop frames)
    ```

## How to Run

1.  Navigate to the directory containing `main.py` in your terminal or command prompt.
2.  Run the application using Python:
    ```bash
    python main.py
    ```

The pet companion will appear on your desktop, and a system tray icon will be visible.

## Usage

* **Pet Movement:** The pet will move randomly around your desktop.
* **Dragging the Pet:** Click and drag the pet to move it manually.
* **Interacting with the Pet:** Click the pet multiple times to see different reactions (e.g., "Hurt" animation). If clicked too many times, the pet will play a "Dead" animation and stop moving.
* **System Tray Icon (Right-Click):**
    * **Hide Pet / Show Pet:** Toggles the visibility of the pet on the desktop.
    * **Open Control Box:** Opens a small window with manual movement controls (Up, Down, Left, Right, Jump, Slide).
    * **Disable Audio / Enable Audio:** Toggles the pet's sounds.
    * **Food -> Add Random Food:** Spawns a random food item on your desktop. The pet will automatically try to chase and "eat" it. You can also drag the food items around.
    * **Food -> Clear All Food:** Removes all food items from the desktop.
    * **Poop -> Add Random Poop:** Manually spawns a random poop item near the pet.
    * **Poop -> Clear All Poop:** Removes all poop items from the desktop.
    * **Revive Pet:** If your pet is "dead", this option will become active, allowing you to reset its state and bring it back to life.
    * **Change Pet Type:** Switch between a cat and a dog companion.
    * **Exit:** Quits the application.

* **Control Box (when open):**
    * Use the "Up", "Down", "Left", "Right" buttons to move the pet.
    * Click "Jump" to make the pet jump.
    * Click "Slide" to make the pet slide.
    * Click "Stop" to halt manual movement.
    * You can also use `W`, `A`, `S`, `D` keys for movement, `Space` for jump, and `Shift` for slide when the control box has focus.

* **Cleaning Poop:** Simply click on a poop item on the desktop to make it disappear.

## Troubleshooting

* **"Error: Default 'assets/cat' directory not found..."**: Ensure the `assets/cat` folder and its contents are correctly placed relative to `main.py`.
* **"Warning: 'assets/food' directory not found..."**: Ensure the `assets/food` folder and its contents are correctly placed. Food features will not work without them.
* **"Warning: 'assets/poop' directory not found..."**: Ensure the `assets/poop` folder and its contents are correctly placed. Poop features will not work without them.
* **Pet not moving or animating after dying**: If the pet is dead, it will remain in its final "Dead" frame and stop all movement/animations. Use the "Revive Pet" option in the system tray to bring it back.
* **Food not visible**: Ensure `FOOD_SIZE` in `main.py` matches the actual pixel dimensions of your food sprites (currently set to 40). Also, ensure you are using the "Add Random Food" option from the tray menu.
* **Poop not visible**: Ensure `POOP_SIZE` in `main.py` matches the actual pixel dimensions of your poop sprites (currently set to 25). Also, ensure you are using the "Add Random Poop" option or waiting for automatic spawns.
