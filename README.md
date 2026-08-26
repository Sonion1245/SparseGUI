# SparseGUI

 Fully built retained-mode GUI library built using python meant for pygame wihout needing to manually draw rects and poll actions done to them. 

 ## How to install
 Beofre starting you will need to install python. To install watch this https://www.youtube.com/watch?v=YKSpANU8jPE 
 Make sure to first install pygame with the command ```pip install pygame```. To be able to use the library first download the file then add it to your project. It should appear in the top most of the dir.

## Features
 * Elements
    * ImageLabel
    * TextButton
    * ImageButton
    * TextBox
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

## Example Script
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
    canvas = SparseGUI.Canvas(WINDOW_SIZE, [
        SparseGUI.SubWindow((150, 150), title="My Example SparseGUI Window!", children=[
            SparseGUI.TextButton("Click me!", action=lambda: print("[EVENT LOG]: Click me clicked!"), background_color=(45, 45, 45)),
            SparseGUI.TextBox(on_focus_lost=lambda enter, _: print(f"[EVENT LOG]: Textbox lost focus, exited from enter: {enter}"), 
                              on_focus=lambda: print("[EVENT LOG]: Textbox gained focus!"), clear_text_on_focus=False),
            SparseGUI.TextBox().set_as_label(True).set_single_text("Text label!")
        ]).add_component(SparseGUI.ResizeableComponent)[0].apply_layout(SparseGUI.VerticalLayout, item_gap=10).set_scrollable(False) # Auto sorts the elements in positioning.
    ])

    # Starting game loop.
    running, clock = True, pygame.time.Clock()
    while running:
        # Gettings events and time between frames.
        dt, events = clock.tick(WINDOW_FPS) / 1000, pygame.event.get()

        #  Updating and handling events.

        # Checking for quitting the window.
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            
            # Handling canvas elements.    
            canvas.handle_event(event)

        # Updating elements.
        canvas.update(dt)

        root.fill((45, 45, 45))

        canvas.draw(root)
    
        # Show current frame.
        pygame.display.flip()
    
    # Quit out the program and clean up pygame.
    pygame.quit()
    exit()

# Running main.
if __name__ == "__main__":
    main()

# Running main.
if __name__ == "__main__":
    main()

```
