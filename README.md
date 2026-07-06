# SparseGUI

 Fully built retained-mode GUI framework built using python meant for pygame wihout needing to manually draw rects and poll actions done to them. 

 ## How to install
 **Make sure to first install pygame with the command** ```pip install pygame```. To be able to use the library first download the file then add it to your project. It should appear in the top most of the dir.

## Features
 * Elements
    * TextLabel
    * ImageLabel
    * TextButton
    * ImageButton
    * TextBox
    * MultiLineTextBox
    * Bar
    * Menu
    * CheckBox
    * SubWindow

* Allows for auto positioning of elements
* Scene graph style element
* Z ordering of elements
* Coordinate System
* Composition Component System
* Layout System
* Cached text surfaces.

Example script to start with
```python


# Imports.

import pygame, SparseGUI
from sys import exit

# Starting SparseGUI and setting constants.

SparseGUI.init()
WINDOW_SIZE = (800, 600) # Size of the pygame window.
WINDOW_FPS = 60 # What FPS the window should run at.

# Main
def main():
    # Setting up window
    root = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("SparseGui Example Script Window")

    # Canvas object to place SparseGUI elements inside.
    # Add SparseGUI elements inside the list for them to appear inside the screen.
    # This will be the top level of the scene graph of the elements.
    canvas = SparseGUI.Canvas(root, WINDOW_SIZE, [
        SparseGUI.SubWindow((150, 150), title="My Example SparseGUI Window!", children=[
            SparseGUI.TextButton("Click me!", action=lambda: print("[EVENT LOG]: Click me clicked!"), background_color=(45, 45, 45)),
            SparseGUI.TextBox(placeholder_text="Type in here...", background_color=(20, 20, 20),
                              on_focus_lost=lambda enter, text: print("[EVENT LOG]: Textbox focus lost!")),
            SparseGUI.TextLabel("Text label!")
        ]).add_component(SparseGUI.ResizeableComponent).apply_layout(SparseGUI.VerticalLayout, item_gap=10) # Auto sorts the elements in positioning.
    ])

    # Starting game loop.
    running, clock = True, pygame.Clock()
    while running:
        # Gettings events and time between frames.
        dt, events = clock.tick(WINDOW_FPS) / 1000, pygame.event.get()

        #  Updating and handling events.

        # Checking for quitting the window.
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        # Handling canvas elements.    
        canvas.handle_events(events)

        # Updating and drawing elements.

        root.fill((45, 45, 45))

        # Updating the canvas for elements to appear. dt is passed so tweening and frame based animations work correctly.
        canvas.update(dt)

        # Show current frame.
        pygame.display.flip()
    
    # Quit out the program and clean up pygame.
    pygame.quit()
    exit()

# Running main.
if __name__ == "__main__":
    main()

```
