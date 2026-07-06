
'''
    SparseGUI
    -
    
    Retained-mode UILibrary written in python 3.13.3 pygame 2.6.1. Allows for well running and comprehensive UI in pygame in a parent child 
    hierarchy without needing to manually drawn to surfaces. Allows for easier GUI work and has a built set of diverse GUI elements.
'''

# ----------------------------
# IMPORTS
# ---------------------------

# Getting modules/classes
import pygame as _pygame
import time as _time
import sys as _sys
from enum import Enum as _Enum
from typing import Any as _Any
from typing import Self as _Self
from typing import Callable as _Callable
from typing import Literal as _Literal
from uuid import uuid4 as _uuid4

# ----------------------------
# GLOBALS
# ----------------------------

pygame_event_type = _pygame.event.Event
Coordinate = tuple[int, int]; # Coordinate

_global_font = None # The global font used by the library as a placeholder for fonts not given to elements.

def init(global_font_name="consolas", global_font_size=15) -> bool:
    global _global_font
    
    if not _pygame.get_init():
        _pygame.init()

    _global_font = _pygame.font.SysFont(global_font_name, global_font_size)

    return True

# Decodes null bytes inside clipboard text and returns the final product.
def get_clipboard_text() -> str:
    copied_text = _pygame.scrap.get(_pygame.SCRAP_TEXT)
    if not copied_text:
        return ""

    try:
        text = copied_text.decode("utf-8", errors="ignore")
    except: # tbh dont know what could go wrong here.
        text = copied_text.decode(errors="ignore")

    text = text.replace("\x00", "")

    return text

# Changes the cursor hand based off a toggle for the arrow and hand.
def set_cursor_hand(enabled: bool) -> None:
    _pygame.mouse.set_system_cursor(_pygame.SYSTEM_CURSOR_HAND if enabled else _pygame.SYSTEM_CURSOR_ARROW)

# Holds colors via str to tuple pairs
COLORS = {
    "BLACK": (0, 0, 0),
    "WHITE": (255, 255, 255),
    "GRAY": (25, 25, 25),
    "LIGHTER-GRAY": (45, 45, 45),
    "DARKER-GRAY": (15, 15, 15),
    "RED": (255, 23, 23),
    "BLUE": (23, 23, 255),
    "DARKER-WHITE": (125, 125, 125),
    "GREEN": (23, 255, 23),
    "LIGHTER-BLUE": (99, 188, 227),
    "COOKIE-CUTTER-BROWN": (139, 90, 43),
    "DARKER-BLUE": (23, 23, 125),
    "CYAN": (0, 255, 255),
    "PURPLE": (128, 0, 128),
    "YELLOW": (255, 255, 0),
    "DARK": (10, 10, 10),
    "PURE-GREEN": (0, 255, 0),
    "TRANSPARENT": (0, 0, 0, 0)
}

# ----------------------------
# ENUMS
# ----------------------------

# Easy way to add modes to elements. In this case Menus.
class LayoutAlignment(_Enum):
    '''
        The Layout enums for Menu layouts.
    '''
    left = 0
    up = 1
    center = 2
    down = 3
    right = 4

class TextXAlignment(_Enum):
    '''
        Determines where text goes inside elements on the X axis (Button, TextLabel are supported currently).
    '''
    left = 0
    middle = 1
    right = 2

class TextYAlignment(_Enum):
    '''
        Determines where text goes inside elements on the Y axis (Button, TextLabel are supported currently).
    '''
    top = 0
    middle = 1
    bottom = 2

# ----------------------------
# HELPER CLASSES
# ----------------------------

class _Stack:
    '''
        A basic stack implementation.
    '''
    def __init__(self, start_list: list[_Any]=None):
        self.list = start_list or []
        self.original = self.list.copy()
        self.history = []
        
    def _log_change(self, item: _Any):
        self.history.append(item)
        
    def start_over(self):
        self.list = self.original.copy()
        
    def insert(self, value: _Any):
        self._log_change(("insert", value))
        self.list.append(value)
        
    def pop(self):
        self._log_change(("pop", self.list[-1]))
        self.list.pop()
        
    def reset(self):
        self._log_change(("reset", self.list.copy()))
        self.list.clear()
        
    def get_last_change(self):
        return self.history[-1]

    def _get_element(self, i: int):
        try:
            return self.history[i]
        except IndexError as e:
            return None

    def undo(self, times: int=1):
        for _ in range(times):
            change = self._get_element(-1)
            if not change:
                continue
            self.wrapper_event(change[1], change[0])  

            if change[0] == "pop":
                self.list.append(change[1])
            elif change[0] == "insert":
                self.list.pop()
            elif change[0] == "reset":
                self.list[:] = change[1]

            self.history.remove(change)
        
    def wrapper_event(self, value=None, context=None):
        if hasattr(self, "on_undo"):
            self.on_undo(context, value) 

    def __repr__(self):
        return f"Stack(start_list={self.list})"

    def __str__(self):
        return f"Stack: {self.list}"

class _Tween:
    def __init__(self, start: _Any, end: _Any, setter: _Callable, duration: float=1, on_end: _Callable[[], None]=None):
        self.start = start
        self.end = end
        self.duration = max(duration, 0.0001)
        self.setter = setter
        self.start_time = _time.time()
        self.finished = False
        self.elapsed_time = 0
        self.on_end = on_end

    def update(self, dt: float) -> None:
        self.elapsed_time += dt
        t = min(1.0, self.elapsed_time / self.duration)

        if isinstance(self.start, tuple):
            value = tuple(self.start[i] + (self.end[i] - self.start[i]) * t for i in range(len(self.start)))
        elif isinstance(self.start, str) or isinstance(self.end, str):
            raise NotImplementedError("Can not tween strings")
        else:
            value = self.start + (self.end - self.start) * t

        self.setter(value)

        if t >= 1.0:
            self.finished = True
            if callable(self.on_end):
                self.on_end()

# ----------------------------
# CANVAS
# ----------------------------

class Canvas:
    '''
    The Canvas at which the top level widgets parented to. Call .update([event list here]) inside a game loop.\n
    **layer**: list[UIElement] | UIelement | None
    '''
    def __init__(self, draw_surface: _pygame.Surface, screen_size: Coordinate=(500, 400), layer: list | None=None, 
                 fill_color: tuple[int, int, int]=COLORS["TRANSPARENT"], position: Coordinate=(0, 0)):
        self.layer = layer or []
        self.hidden = False
        self.surface = _pygame.Surface(screen_size, _pygame.SRCALPHA)
        self.clip_root = True
        self.fill_color = fill_color
        self.draw_surface = draw_surface
        self.position = position

        if self.layer:
            for element in layer:
              element.parent = self

    def add_element(self, element):
        element.parent = self
        self.layer.append(element)

    @property
    def size(self):
        return self.surface.get_size()
    
    @size.setter
    def size(self, value: Coordinate):
        self.surface = _pygame.Surface(value, _pygame.SRCALPHA)

    def destroy(self):
        '''
            Destroys the Canvas and its layer.
        '''

        self.hidden = True
        self.fill_color = COLORS["TRANSPARENT"]
        self.draw_surface = None
        
        for element in self.layer:
            element.destroy()
        
        self.surface = None
        
              
    def get_gui_on_point(self, point: Coordinate):
        '''
            Gets all elements in the Canvas overlapping this point in screen space.
        '''
        results = []

        def walk(item: UIElement):
            if item.hidden:
                return
            
            local_point = item.transform_point_to_local_space(point)
            
            if item.surface.get_rect(topleft=item.position).collidepoint(local_point):
                results.append(item)
            
            for child in item.children:
                walk(child)
        
        for element in self.layer:
            walk(element)
        
        return results

    def get_size(self) -> Coordinate:
        return self.surface.get_size()

    def handle_events(self, events: list[pygame_event_type]):
        '''
            Handles the element events.
        '''
        if isinstance(self.layer, list):
            for element in self.layer:
                if element.hidden: continue
                for event in events:
                    element.handle_event(event)
        else:
            if not self.layer.hidden:
                for event in events:
                    self.layer.handle_event(event)

    def update(self, dt: float):
        ''' Updates .layer elements then draws them. '''
        if self.hidden: return

        self.surface.fill(self.fill_color)

        self.layer.sort(key=lambda a: a.Z)

        if self.layer:
            if isinstance(self.layer, list):
                for element in self.layer:
                    if element.hidden: continue

                    element.update(dt)
                    element.draw(self.surface if self.clip_root else self.draw_surface)
            else:
                self.layer.update(dt)
                self.layer.draw(self.surface if self.clip_root else self.draw_surface)

        self.draw_surface.blit(self.surface, self.position)

# ----------------------------
# BASE CLASSES
# ----------------------------

class UIElement:
    '''
        The base class of a UI element.\n
        NOTE: Elements overlapping can take input at the same time, no fix is found yet.
    '''
    def __init__(self, 
                 parent: _Self | Canvas=None, size: Coordinate=(100, 50), position: Coordinate=(0, 0), 
                 background_color: tuple[int, int, int]=None, stroke_thickness: int=4, stroke_color: tuple[int, int, int]=COLORS["BLACK"], 
                 children: list[_Self]=None, border_radius: int=0, name: str="UIElement"):
        self.element_id = _uuid4()
        self.children = children or []
        self.components: list[UIComponent] = []
        self.parent = parent
        self.hidden = False
        self.background_color = background_color or COLORS["DARKER-GRAY"]
        self.position = position
        self._size = size
        self.surface = _pygame.Surface(self.size, _pygame.SRCALPHA).convert_alpha()
        self.stroke_thickness = stroke_thickness
        self.stroke_color = stroke_color
        self.name = name
        self.screen_position = (0, 0)
        self.local_mouse_position = (0, 0)
        self.mouse_hovering = False
        self._active_tweens: list[_Tween] = []

        self.Z = 1
        self.border_radius = border_radius

        for v in self.children:
            v.parent = self
    
    def transform_point_to_local_space(self, point: Coordinate) -> Coordinate:
        '''
            Transforms the given point to the local space of the parent element. 
        '''
        selected = self.parent

        while selected:
            point = (
                point[0] - selected.position[0],
                point[1] - selected.position[1] + (selected.scroll_y if isinstance(selected, Menu) else 0) - (selected.title_bar_height if isinstance(selected, SubWindow) else 0)
            )

            selected = selected.parent if hasattr(selected, "parent") else None

        return point

    def get_border_radius(self, offset: int=3) -> int:
        return (self.border_radius+offset if self.border_radius > 0 else -1)
    
    def get_canvas(self) -> Canvas:
        current = self.parent

        while not isinstance(current, Canvas):
            current = current.parent
        
        return current

    def add_component(self, componet_type, *args, **kwargs) -> _Self:
        '''
            This adds a componet (UIComponent) to the element.
        '''
        componet_ins = componet_type(self, *args, **kwargs)
        componet_ins.init()

        self.components.append(componet_ins)
        return self

    def remove_component(self, componet_instance) -> _Self:
        '''
            This removes a componet (UIComponent) to the element.
        '''
        if componet_instance in self.components:
            componet_instance.element = None
            self.components.remove(componet_instance)

        return self

    def update_components(self):
        '''
            Goes through and updates all active componets.
        '''

        self.components.sort(key=lambda a: a.priority)

        for comp in self.components:
            if not comp.active: continue
            comp.update()

    def handle_event_components(self, event: pygame_event_type):
        '''
            Passes the event to all the componets.
        '''

        for comp in self.components:
            if not comp.active: continue
            comp.handle_event(event)

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value: Coordinate):
        self._size = value
        self.update_surface()
    
    @property
    def center(self):
        return (
            self.position[0]-self.size[0]/2,
            self.position[1]-self.size[1]/2
        )

    @center.setter
    def center(self, center: Coordinate):
        self.position = (
            center[0]-self.size[0]/2,
            center[1]-self.size[1]/2
        )
    
    @property
    def relative_position(self):
        return (
            self.position[0] / self.parent.size[0] if not isinstance(self.parent, Canvas) else 1,
            self.position[1] / self.parent.size[1] if not isinstance(self.parent, Canvas) else 1
        )

    @relative_position.setter
    def relative_position(self, value: Coordinate):
        self.position = (
            self.parent.size[0] * value[0],
            self.parent.size[1] * value[1]
        )
    
    @property
    def relative_size(self):
        return (
            self.size[0] / self.parent.size[0],
            self.size[1] / self.parent.size[1]
        )

    @relative_size.setter
    def relative_size(self, value: Coordinate):
        self.size = (
            self.parent.size[0] * value[0],
            self.parent.size[1] * value[1]
        )

    def _get_scrollbar_rect(self, scroll_y: float, max_scroll: float, scrollbar_size: Coordinate) -> tuple[float, float, float, float]:
        try:
            scroll_percent = max(0, min(scroll_y / max_scroll, 1))
        except ZeroDivisionError as e:
            scroll_percent = 0.1

        scrollbar_y = scroll_percent * (
            self.surface.get_height() - scrollbar_size[1]
        )

        return (
                self.surface.get_width()-scrollbar_size[0],
                scrollbar_y,
                scrollbar_size[0],
                scrollbar_size[1]
        )

    def destroy(self) -> None:
        '''
            Removes this element from its parent and recursively destroys all children.
        '''
        for child in self.children.copy(): # Calling destroy on all the children in return makes then destroy theyre
            child.destroy()
        
        self.children.clear()
        self.components.clear()

        if self.parent:
            if not isinstance(self.parent, Canvas) and self in self.parent.children:
                self.parent.children.remove(self)
            elif isinstance(self.parent, Canvas) and self in self.parent.layer:
                self.parent.layer.remove(self)
            
            self.parent = None

        self._active_tweens.clear()

        self.surface = None

    def get_stroke_rect(self) -> _pygame.Rect:
        '''
            Gets the elements stroke rect. This is purely meant for drawing and shouldnt be used for anything else.
        '''
        return _pygame.Rect(self.position[0]-self.stroke_thickness, self.position[1]-self.get_menu_scroll()-self.stroke_thickness,
                self.surface.get_width()+self.stroke_thickness*2, self.surface.get_height()+self.stroke_thickness*2)

    def tween_position(self, target_position: Coordinate, duration: float=0.2, on_end: _Callable[[], None]=None) -> _Self:
        '''
            Tweens the elements position to the target position over the duration.
        '''
        def setter(v: Coordinate):
            self.position = v
        
        self._active_tweens.append(_Tween(self.position, target_position, setter, duration, on_end))
        return self

    def tween_size(self, target_size: Coordinate, duration: float=0.2, on_end: _Callable[[], None]=None) -> _Self:
        '''
            Tweens the elements size to the target size over the duration.
        '''
        def setter(v: Coordinate):
            self.size = v
        
        self._active_tweens.append(_Tween(self.size, target_size, setter, duration, on_end))
        return self

    def add_child(self, child: _Self) -> _Self:
        ''' Adds a child to the element. This doesnt have to be the assigned type and can be any element. '''

        assert isinstance(child, UIElement), "Child is not a element."

        self.children.append(child)
        child.parent = self

        return self
    
    def remove_child(self, child: _Self) -> _Self:
        ''' Removes a child from the element. This doesnt have to be the assigned type and can be any child.'''

        assert isinstance(child, UIElement), "Child is not a element."

        self.children.remove(child)
        child.parent = None

        return self

    def add_children(self, children_list: list[_Self]) -> _Self:
        '''
            Adds the list of children to the element.
        '''

        for new_child in children_list:
            self.add_child(new_child)
        
        return self

    def on_mouse_hover_callback(self, entering: bool, mouse_enter_pos: Coordinate) -> None:
        '''
            A callback for when the mouse enters or leaves the element.\n
            Use this is you intend on hover logic.
        '''
    
    def on_mouse_hover(self, entering: bool, mouse_enter_pos: Coordinate) -> None:
        '''
            A callback for when the mouse enters or leaves the element.\n
            **NOTE: This is for internal use.**
        '''

    def child_off_bounds(self, child: _Self) -> bool:
        '''
            Checks if a child is inside the bounds of the element. If it isnt a child it just returns False.
        '''

        if not child in self.children:
            return False

        child_top = child.position[1] - (self.scroll_y if isinstance(self, Menu) else 0) + (
            self.title_bar_height if isinstance(self, SubWindow) else 0)

        child_bottom = child_top + child.size[1]

        child_left = child.position[0]
        child_right = child_left + child.size[0]

        return (
            child_bottom < 0 or
            child_top > self.size[1] or
            child_right < 0 or
            child_left > self.size[0]
        )

    def get_menu_scroll(self) -> int:
        '''
            Gets the elements parent scroll_y offset. Only if the parent is a Menu or just returns 0
        '''
        return self.parent.scroll_y if isinstance(self.parent, Menu) else 0

    def get_subwindow_offset(self) -> int:
        '''
            Gets the title_bar_height offset if the parent is a SubWindow. Otherwise just returns 0
        '''
        return self.parent.title_bar_height if isinstance(self.parent, SubWindow) else 0

    def get_children(self) -> dict[str, _Self]:
        '''
            Gets all the children in a dict. This returns all UI elements not just the selected type.
        '''
        children = {}
        for child in self.children:
            children[child.name] = child
        
        return children

    def mouse_over_parent(self) -> bool:
        '''
            Checks if the mouse if over the top most parent of the element. The top most parent is the parent's parent.
        '''
        if not self.parent:
            return True

        mouse_over_parent = True
        current = self.parent
        while current:
            if isinstance(current, Canvas):
                break
            
            if not current.surface.get_rect(topleft=current.screen_position).collidepoint(_pygame.mouse.get_pos()):
                mouse_over_parent = False
                break
            
            current = current.parent
        
        return mouse_over_parent
    
    def mouse_over_element(self) -> bool:
        '''
            Returns wether the mouse is over the element based off screen position.
        '''
        return self.surface.get_rect(topleft=self.screen_position).collidepoint(_pygame.mouse.get_pos())

    def hide(self) -> _Self:
        if self.mouse_hovering and self.mouse_over_parent():
            _pygame.mouse.set_system_cursor(_pygame.SYSTEM_CURSOR_ARROW)
        self.hidden = True
        return self

    def update(self, dt: float) -> None:
        self.screen_position = self.get_screen_position()
        self.local_mouse_position = self.get_local_mouse_position()

        if not self.mouse_hovering and self.mouse_over_element():
            args = (True, self.local_mouse_position)
            self.on_mouse_hover(*args)
            self.on_mouse_hover_callback(*args)

        if self.mouse_hovering and not self.mouse_over_element():
            args = (False, self.local_mouse_position)
            self.on_mouse_hover(*args)
            self.on_mouse_hover_callback(*args)

        self.mouse_hovering = self.surface.get_rect(topleft=self.position).collidepoint(self.local_mouse_position)
        self.update_components()

        for element in self.children:
            element.update(dt)
        
        for tween in self._active_tweens.copy():
            tween.update(dt)
            if tween.finished and tween in self._active_tweens:
                self._active_tweens.remove(tween)

    def set_Z(self, Z: int) -> _Self:
        self.Z = Z
        return self

    def set_center(self, center: Coordinate) -> _Self:
        '''
            Sets the center property of the element. This should be used in method chaining and not practical use.
        '''
        self.center = center
        return self

    @staticmethod
    def _key(a: _Self):
        return a.Z

    def draw_elements(self, target_surface: _pygame.Surface) -> None:
        self.children.sort(key=self._key)

        for element in self.children:
            if self.child_off_bounds(element): continue
            if element.hidden: continue
            if element.size <= (0, 0): continue

            element.draw(target_surface)
        
    def handle_event_elements(self, event: pygame_event_type) -> None:        
        self.handle_event_components(event)

        for element in self.children:
            if not hasattr(element, "handle_event"): continue
            if self.child_off_bounds(element) and not isinstance(element, SubWindow): continue
            if element.hidden: continue
            if element.size <= (0, 0): continue

            element.handle_event(event)

    def get_local_mouse_position(self) -> Coordinate:
        '''
            Returns the mouse position transformed into the local space of the elements parent.
        '''
        pos = _pygame.mouse.get_pos()
        if not self.parent:
            return pos
        
        pos = self.transform_point_to_local_space(pos)

        return pos

    def get_screen_position(self) -> Coordinate:
        '''
            Returns the elements position transformed into screen position.
        '''
        pos = self.position
        if not self.parent:
            return pos

        selected = self.parent
        while selected:
            pos = (
                pos[0] + selected.position[0],
                pos[1] + selected.position[1] - (selected.scroll_y if isinstance(selected, Menu) else 0) + (selected.title_bar_height if isinstance(selected, SubWindow) else 0)
            )

            selected = selected.parent if hasattr(selected, "parent") else None
        
        return pos

    def get_rect(self) -> tuple[int, int, int, int]:
        '''
            Returns the elements rect style dimensions. Simply pass the return value in pygame.Rect to get an actual rect result.
        '''
        return (
            self.position[0],
            self.position[1],
            self.size[0],
            self.size[1]
        )

    def update_surface(self) -> _Self:
        self.surface = _pygame.Surface(self.size, _pygame.SRCALPHA).convert_alpha()
        return self

    def draw(self, target_surface: _pygame.Surface) -> None:
        ''' Draws the element to the given surface. This is a placeholder and just draws a blanket element. Use this as a 
        templete for making custom widgets. This is meant to be overriden if you intend on custom drawing.
        '''
        self.surface.fill(COLORS["TRANSPARENT"])
        pos = (self.position[0], self.position[1]-self.get_menu_scroll())
        _pygame.draw.rect(target_surface, self.stroke_color, self.get_stroke_rect(), border_radius=self.get_border_radius())
        _pygame.draw.rect(target_surface, self.background_color, (*pos, *self.size), border_radius=self.get_border_radius(0))
        target_surface.blit(self.surface, pos)
    
    def handle_event(self, event: pygame_event_type) -> None:
        ''' Handles the element interactivity. This is a placeholder and just handles components until overriden '''
        ...
        self.handle_event_components(event)

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return str(self)

    def __eq__(self, value: _Self):
        if isinstance(value, UIElement):
            return self.element_id == value.element_id

        raise NotImplementedError(f"The data type of ({type(value)}) is not implemented.")
    
    def __ne__(self, value):
        if isinstance(value, UIElement):
            return self.element_id != value.element_id

        raise NotImplementedError(f"The data type of ({type(value)}) is not implemented.")

class UIComponent:
    '''
        Base class for a UI componet. These modify theyre element (UIElement) in any way.\n
        These Components are used internally and are usable externally. May not be compatable for all elements.
    '''
    def __init__(self, element: UIElement, active: bool=True):
        self.component_id = _uuid4()
        self.element = element
        self.active = active
        self.priority = 1
    
    def handle_event(self, event: pygame_event_type) -> None:
        '''
            Handles event for the componet. This is meant to be overriden and current does nothing.
        '''
        ...


    def init(self) -> None:
        '''
            Initalizes the componet. This is meant to be overriden and currently does nothing.
        '''
        ...
    
    def update(self) -> None:
        '''
            This updates the componet. This is meant to be overriden and currently does nothing.
        '''
        ...
    
    def __eq__(self, value: _Self):
        if isinstance(value, UIComponent):
            return self.component_id == value.component_id
        
        raise NotImplementedError(f"The data type of ({type(value)}) is not implemented.")

class MenuLayout:
    '''
        Base class for Menulayouts. To sub class this make sure to define the base_update().\n
        NOTE: These are meant to directly edit elements positions inside the parent Menu.
    '''
    def __init__(self, parent, item_gap: int=25, horizontal_padding: int=5, vertical_padding: int=5, name: str="BaseUILayout"):
        self.parent = parent
        self.item_gap = item_gap
        self.horizontal_padding = horizontal_padding
        self.vertical_padding = vertical_padding
        self.enabled = True
        self.origin_pos_elements = [element.position for element in parent.children]
        self.name = name
    
    def switch_enabled(self, enabled: bool) -> _Self:
        self.enabled = enabled
        return self

    def update(self) -> None:
        if not self.enabled:
            return

        if hasattr(self, "base_update") and callable(self.base_update):
            self.base_update()
    
    def __str__(self):
        return self.__class__.__name__

# ----------------------------
# COMPONENTS
# ----------------------------

class DragComponent(UIComponent):
    '''
        Add dragability to any element.
    '''
    def __init__(self, element: UIElement, active: bool=True, offset: Coordinate=(0, 0)):
        super().__init__(element, active)
        self.drag_offset = (0, 0)
        self.dragging = False
        self.offset = offset

    def drag_start(self):
        '''
            A callback for when the componnent starts dragging. This is meant to be overriden and does nothing.
        '''
        ...
    
    def drag_end(self):
        '''
            A callback for when the componnent ends dragging. This is meant to be overriden and does nothing.
        '''
        ...

    def should_start_drag(self, mouse_pos: Coordinate) -> bool:
        '''
            Indicates wehter the component should start dragging. This is meant to be overriden and just returns True
        '''
        return True
    def handle_event(self, event: pygame_event_type):
        if event.type == _pygame.MOUSEBUTTONDOWN and event.button == 1 and self.element.mouse_hovering and not self.element.hidden:
            if self.should_start_drag(event.pos):
                self.drag_offset = (
                    event.pos[0] - self.element.screen_position[0],
                    event.pos[1] - self.element.screen_position[1]
                )
                self.dragging = True
                self.drag_start()
        
        if event.type == _pygame.MOUSEMOTION and self.dragging:
            mouse_pos = self.element.local_mouse_position
            self.element.position = (
                mouse_pos[0] - self.drag_offset[0] + self.offset[0],
                mouse_pos[1] - self.drag_offset[1] + self.offset[1]
            )

        if event.type == _pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            self.dragging = False
            self.drag_end()

class ClickableComponent(UIComponent):
    '''
        Adds clickability to any element.
    '''
    def __init__(self, element: UIElement, active: bool=True, on_click: _Callable=lambda: print("Hello world!")):
        super().__init__(element, active)
        self.on_click = on_click

    def should_click(self, mouse_pos: Coordinate) -> bool:
        '''
            Indicates if the component should preform a click. This is meant to be overriden and currently returns True.
        '''
        return True

    @staticmethod
    def _clickable(element):
        return isinstance(element, UIElement) and isinstance(element, TextButton) and element.clickable

    def is_icons_clickable(self) -> bool:
        if not self.element.parent:
            return False
    
        for element in self.element.children:
            if self._clickable(element):
                if element.mouse_hovering:
                    return True
        
        if isinstance(self.element.parent, UIElement):
            for element in self.element.parent.children:
                if element is self.element:
                    continue
                if self._clickable(element):
                    if element.mouse_hovering:
                        return True
        
        return False

    def on_mouse_hover(self, entering, mouse_enter_pos):
        if not self.active:
            return
        
        if self.element.clickable and not self.is_icons_clickable() and not self.element.hidden:
            if hasattr(self.element, "_final_color"):
                self.element._final_color = self.element.background_color if not entering else self.element.selected_color
            
            set_cursor_hand(entering)

    def handle_event(self, event: pygame_event_type):
        if event.type == _pygame.MOUSEBUTTONUP and event.button == 1 and self.active:
            if self.is_icons_clickable():
                return

            if self.element.mouse_hovering and self.element.mouse_over_parent() and self.should_click(event.pos):
                self.on_click()

class ResizeableComponent(UIComponent):
    '''
        Adds resizability to any element.
    '''
    def __init__(self, element: UIElement, active: bool=True, min_size: Coordinate=(15, 15)):
        super().__init__(element, active)
        self.priority = 2
        self.resizing = False
        self.resize_range = 15
        self.min_size = min_size
        self._mode = "bottomright"

    def should_resize(self, mouse_pos: Coordinate) -> bool:
        '''
            This indicates wether the component should start resizing. This should be overriden and current returns True
        '''
        return True

    def handle_event(self, event: pygame_event_type):
        if event.type == _pygame.MOUSEBUTTONDOWN and self.element.mouse_hovering and self.element.mouse_over_parent() and not self.element.hidden:
            mouse_pos = _pygame.mouse.get_pos()
            _new_rect = _pygame.Rect(
                self.element.size[0]-self.resize_range+self.element.screen_position[0],
                self.element.size[1]-self.resize_range+self.element.screen_position[1],
                self.resize_range,
                self.resize_range
            )

            result = _new_rect.collidepoint(mouse_pos)

            def check_side(i: int):
                return(self.element.screen_position[i] + self.element.size[i] - self.resize_range < mouse_pos[i] and 
                    self.element.screen_position[i] + self.element.size[i] > mouse_pos[i])

            if not result:
                if check_side(0):
                    self.resizing = True
                    self._mode = "right"
                elif check_side(1):
                    self._mode = "bottom"
                    self.resizing = True
            else:
                self._mode = "bottomright"
                self.resizing = True
        
        if event.type == _pygame.MOUSEMOTION and self.resizing:
            mouse_pos = _pygame.mouse.get_pos()

            def calculate_side(i: int):
                return max(self.min_size[i], mouse_pos[i] - self.element.screen_position[i])

            if self._mode == "bottomright":
                self.element.size = (
                calculate_side(0),
                calculate_side(1)
                )
            elif self._mode == "right":
                self.element.size = (
                    calculate_side(0),
                    self.element.size[1]
                )
            elif self._mode == "bottom":
                self.element.size = (
                    self.element.size[0],
                    calculate_side(1)
                )
        if event.type == _pygame.MOUSEBUTTONUP and self.resizing:
            self.resizing = False

# ----------------------------
# WIDGETS SET
# ----------------------------

class TextLabel(UIElement):
    ''' Displayable text as a element. '''
    def __init__(self, text: str="Hello world!", parent: _Self=None, position: Coordinate=(0, 0), text_size: int=15, 
                text_color: tuple[int, int, int]=None, name: str="TextObject", font: _pygame.font.Font=None,
                text_alignment: tuple[TextXAlignment, TextYAlignment]=(TextXAlignment.middle, TextYAlignment.middle)):
        super().__init__(parent, (0, 0), position, (0, 0, 0, 0), 0, children=[], name=name)
        self.font = font or _global_font
        self._text = text
        self.text_color = text_color or COLORS["WHITE"]
        self.cached_text_surface = self.font.render(self.text, True, self.text_color)
        self.size = self.cached_text_surface.get_size()
        self.text_alignment_x = text_alignment[0]
        self.text_alignment_y = text_alignment[1]
    
    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value: str):
        if value == self.text:
            return
        
        self._text = value
        self.cached_text_surface = self.font.render(self.text, True, self.text_color)
        self.size = self.cached_text_surface.get_size()

    def handle_event(self, event: pygame_event_type):
        self.handle_event_components(event)

    def get_text_y_pos(self) -> float:
        '''
            Returns text Y coordinate position based off text alignment.
        '''

        match self.text_alignment_y:
            case TextYAlignment.top:
                return 0
            case TextYAlignment.middle:
                return self.size[1]/2-self.cached_text_surface.get_height()/2
            case TextYAlignment.bottom:
                return self.size[1]-self.cached_text_surface.get_height()

    def get_text_pos(self) -> Coordinate:
        '''
            Returns cached text surface based off text alignment.
        '''

        match self.text_alignment_x:
            case TextXAlignment.left:
                return (0, self.get_text_y_pos())
            case TextXAlignment.middle:
                return (self.surface.get_width()/2-self.cached_text_surface.get_width()/2, 
                        self.get_text_y_pos())
            case TextXAlignment.right:
                return (
                    self.size[0]-self.cached_text_surface.width,
                    self.get_text_y_pos()
                )

    def draw(self, target_surface: _pygame.Surface) -> None:
        self.surface.fill(self.background_color)

        self.surface.blit(self.cached_text_surface, self.get_text_pos())
        target_surface.blit(self.surface, (self.position[0], self.position[1]-self.get_menu_scroll()))

class ImageLabel(UIElement):
    '''
        Displayable image as a element.\n
        **NOTE: This is not compatable with border radius.**
    '''
    def __init__(self, parent: UIElement=None, size: Coordinate=(100, 100), position: Coordinate=(0, 0), 
                stroke_thickness: int = 4, stroke_color: tuple[int, int, int] = COLORS["BLACK"], 
                children: list[UIElement]=None, name: str="Image Label", image: _pygame.Surface=None):
        super().__init__(parent, size, position, (0, 0, 0, 0), stroke_thickness, stroke_color, children, name)
        self._image: _pygame.Surface = image.convert_alpha() if image else _pygame.Surface((0, 0)) 
        self.set_size(size)

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value: _pygame.Surface):
        self._image = _pygame.transform.scale(value, self.size)

    def set_size(self, size: Coordinate) -> _Self:
        self.size = size
        self.image = self._image
        return self

    def handle_event(self, event: pygame_event_type):
        self.handle_event_components(event)

    def draw(self, target_surface: _pygame.Surface):
        self.surface.fill(self.background_color)
        self.surface.blit(self._image, (0, 0))
        _pygame.draw.rect(target_surface, self.stroke_color, self.get_stroke_rect())
        target_surface.blit(self.surface, (self.position[0], self.position[1]-self.get_menu_scroll()))

class TextButton(UIElement):
    '''
        A clickable button that displays text. This should be used when you want a action to happen when an element is clicked on.
    '''
    def __init__(self, text: str="Hello world!", position: Coordinate=(0,0), action: _Callable=lambda: print("I was clicked!"), size: Coordinate=(100, 35), 
                 background_color: tuple[int, int, int]=None, selected_color: tuple[int, int, int]=None, stroke_color:  tuple[int, int, int]=COLORS["BLACK"], stroke_thickness: int=4,
                 parent: UIElement=None, clickable: bool=True, children: list[UIElement]=None, border_radius: int=0, name: str="Icon", font: _pygame.font.Font | None=None,
                 text_alignment: tuple[TextXAlignment, TextYAlignment]=(TextXAlignment.middle, TextYAlignment.middle)):
        super().__init__(parent, size, position, background_color, stroke_thickness, stroke_color, children=children, name=name, border_radius=border_radius)
        self.hidden = False
        self.clickable = clickable
        self._text = text
        self.text_font = font or _global_font
        self.action = action
        self.selected_color = selected_color or (
            min(255, self.background_color[0] + 45),
            min(255, self.background_color[1] + 45),
            min(255, self.background_color[2] + 45)
        )
        self.cached_text_surface = self.text_font.render(self.text, True, COLORS["WHITE"])
        self.text = self._text
        self._final_color = self.background_color

        self.add_component(ClickableComponent)
        self.components[0].should_click = lambda _: self.clickable
        self.components[0].on_click = self.action

        self.text_alignment_x = text_alignment[0]
        self.text_alignment_y = text_alignment[1]

    @property
    def text(self):
        return self._text
    
    @text.setter
    def text(self, value: str):
        if value == self._text:
            return
        
        self._text = value
        text_size = self.text_font.size(value)
        if text_size[0] > self.size[0]:
            self.size = (text_size[0], self.size[1])
        self.cached_text_surface = self.text_font.render(self.text, True, COLORS["WHITE"])

    def get_text_y_pos(self) -> float:
        '''
            Returns text Y coordinate position based off text alignment.
        '''

        match self.text_alignment_y:
            case TextYAlignment.top:
                return 0
            case TextYAlignment.middle:
                return self.size[1]/2-self.cached_text_surface.get_height()/2
            case TextYAlignment.bottom:
                return self.size[1]-self.cached_text_surface.get_height()

    def get_text_pos(self) -> Coordinate:
        '''
            Returns cached text surface based off text alignment.
        '''

        match self.text_alignment_x:
            case TextXAlignment.left:
                return (0, self.get_text_y_pos())
            case TextXAlignment.middle:
                return (self.surface.get_width()/2-self.cached_text_surface.get_width()/2, 
                        self.get_text_y_pos())
            case TextXAlignment.right:
                return (
                    self.size[0]-self.cached_text_surface.width,
                    self.get_text_y_pos()
                )

    def handle_event(self, event: pygame_event_type) -> None:
        self.handle_event_elements(event)

        if event.type == _pygame.MOUSEBUTTONUP and self.mouse_hovering:
            self._final_color = self.selected_color
    
    def on_mouse_hover(self, entering, mouse_enter_pos):
        self.components[0].on_mouse_hover(entering, mouse_enter_pos)

        if not entering:
            self._final_color = self.background_color

    def draw(self, target_surface: _pygame.Surface) -> None:
        if self.hidden: return
        if self.size[0] <= 0 or self.size[1] <= 0: return

        if self._final_color != self.background_color and _pygame.mouse.get_pressed()[0]:
            self._final_color = self.background_color

        pos = (self.position[0], self.position[1]-self.get_menu_scroll())

        size = self.surface.get_size()
        self.surface.fill(COLORS["TRANSPARENT"])

        self.draw_elements(self.surface)

        self.surface.blit(self.cached_text_surface, self.get_text_pos())
        if self.stroke_thickness > 0: 
            _pygame.draw.rect(target_surface, self.stroke_color, self.get_stroke_rect(), border_radius=self.get_border_radius())
        _pygame.draw.rect(target_surface, self._final_color, (*pos, *self.size), border_radius=self.get_border_radius(0))
        target_surface.blit(self.surface, pos)

class ImageButton(ImageLabel):
    '''
        A clickable button that displays an image.\n
        **NOTE: This is not compatable with border radius.**
    '''
    def __init__(self, parent: UIElement=None, size: Coordinate=(100, 35), position: Coordinate=(0, 0), 
            stroke_thickness: int = 4, stroke_color: tuple[int, int, int] = COLORS["BLACK"], 
            children: list[UIElement]=None, name: str="Image Label", image: _pygame.Surface=None, clickable: bool=True, action: _Callable=lambda: print("I was clicked!")):
        super().__init__(parent, size, position, stroke_thickness, stroke_color, children, name, image)
        self.hidden = False
        self.clickable = clickable
        self.action = action

        self.add_component(ClickableComponent)
        self.components[0].should_click = lambda _: self.clickable
        self.components[0].on_click = self.action

    def on_mouse_hover(self, entering, mouse_enter_pos):
        self.components[0].on_mouse_hover(entering, mouse_enter_pos)

    def handle_event(self, event: pygame_event_type) -> None:
        self.handle_event_elements(event)
      
class TextBox(UIElement):
    ''' 
        A Textbox entry. This should be used for user input string name.
    '''
    def __init__(self, position: Coordinate=(0, 0), size: Coordinate=(250, 25), parent: UIElement=None, no_active_elements: bool=False, 
                 children: list[UIElement]=None, name: str="TextBox", border_radius: int=0, background_color: tuple[int, int, int]=COLORS["DARKER-GRAY"],
                 focused_color: tuple[int, int, int]=COLORS["GRAY"], stroke_color: tuple[int, int, int]=COLORS["BLACK"], 
                 placeholder_color: tuple[int, int, int]=COLORS["LIGHTER-GRAY"], placeholder_text: str="...", clear_text_on_focus: bool=True,
                 on_selected: _Callable[[_Self, pygame_event_type, Coordinate], bool]=None, on_focus_lost: _Callable[[bool, str], None]=None):
        super().__init__(parent, size, position, background_color, children=children, name=name, stroke_thickness=2, border_radius=border_radius, stroke_color=stroke_color)
        self._text = "Hello world!"
        self.placeholder_color = placeholder_color
        self.placeholder_text = placeholder_text
        self.focused_color = focused_color
        self.focused = False
        self.scroll_x = 0
        self.cursor_visible = True
        self.now = _time.time()
        self.cursor_position = len(self.text)
        self.font = _pygame.font.SysFont("consolas", self.surface.get_height()-5)
        self.text_offset_input = 4
        self.clear_text_on_focus = clear_text_on_focus
        self.undo_stack = _Stack([])
        self.on_selected = on_selected
        self.editable = True
        self.held_key = False
        self._held_key_tick = _time.time()
        
        def undo(context: str, value: _Any):
            if value["type"] == "backspace" or value["type"] == "delete" or value["type"] == "char_add":
                self.text = value["ori"]
                self.cursor_position = value["pos"]
        
        color = COLORS["WHITE"] if len(self.text) > 0 else self.placeholder_color
        self.undo_stack.on_undo = undo
        self.cached_text_surface = self.font.render(self.text if len(self.text) > 0 else self.placeholder_text, True, color)

        if on_focus_lost:
            self.on_focus_lost = on_focus_lost

    def on_mouse_hover(self, entering, mouse_enter_pos):
        if self.hidden:
            return
        if not self.editable:
            return
        _pygame.mouse.set_system_cursor(_pygame.SYSTEM_CURSOR_IBEAM if entering else _pygame.SYSTEM_CURSOR_ARROW)

    def on_focus_lost(self, was_enter: bool, text: str):
        '''
            This is a callback for when focus was losted. This is meant to be overriden and does nothing.
        '''
        ...

    def on_focus(self):
        '''
            This is a callback for when the textbox is focused. This is meant to be overriden and does nothing.
        '''
        ...

    def select_text_box(self) -> _Self:
        self.on_focus()
        self.focused = True
        return self

    @property
    def text(self):
        return self._text
    
    @text.setter
    def text(self, value: str):
        if value == self.text:
            return
        
        self._text = value

        color = COLORS["WHITE"] if len(self.text) > 0 else self.placeholder_color

        self.cached_text_surface = self.font.render(self.text if len(self.text) > 0 else self.placeholder_text, True, color)

    def set_cursor_position(self, mouse_pos: Coordinate) -> _Self:
        self.cursor_position = 0

        for i in range(len(self.text) + 1):
            before_text_width = self.font.size(self.text[:i])[0]
            if before_text_width > self.local_mouse_position[0] - self.position[0] + self.scroll_x:
                self.cursor_position = max(0, i)
                break
            else:
                self.cursor_position = i
        
        return self

    def check_bounds(self) -> _Self:
        x_pos = self.get_pixel_x()
        if x_pos + self.scroll_x < self.surface.get_width():
            self.scroll_x = 0

        if x_pos >= self.surface.get_width() - self.text_offset_input:
            self.scroll_x = x_pos - self.surface.get_width() + self.text_offset_input
        if x_pos - self.scroll_x < 0:
            self.scroll_x -= x_pos - self.text_offset_input
        
        return self
            
    def exit_box(self, was_enter: bool) -> _Self:
        self.on_focus_lost(was_enter, self.text)
        return self
    
    def register_undo(self, data: dict[str, _Any]) -> _Self:
        self.undo_stack.insert(data)
        return self

    def remove_char(self) -> _Self:
        if self.cursor_position > 0:
            self.register_undo({
                "ori": self.text,
                "pos": self.cursor_position,
                "type": "backspace"
            })
                    
            self.scroll_x -= self.text_offset_input if self.scroll_x > 0 else 0

            self.text = self.text[:self.cursor_position-1] + self.text[self.cursor_position:]
            self.cursor_position -= 1
            self.check_bounds()
        
        return self

    def start_quick_add(self, char: str | int) -> _Self:
        self.held_key = True
        self._held_key_code = char
        self._held_key_tick = _time.time()

        return self

    def handle_event(self, event: pygame_event_type) -> None:
        self.handle_event_elements(event)
        
        if event.type == _pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.hidden:
            if not callable(self.on_selected):
                result = self.mouse_hovering and self.editable
            else:
                result = self.on_selected(self, event, self.local_mouse_position)

            if not result and self.focused:
                self.exit_box(False)
            elif result:
                self.select_text_box()
                if self.clear_text_on_focus: self.text = ""

            self.focused = result
            if self.focused:
                self.now = _time.time()
                self.cursor_visible = True
                self.set_cursor_position(event.pos)
                if (self.get_pixel_x() - self.scroll_x <= 0 and self.scroll_x > 0) or (self.get_pixel_x() - self.scroll_x >= self.size[0] and self.cursor_position < len(self.text)):
                    self.check_bounds()
        if event.type == _pygame.KEYDOWN and self.focused and self.editable:
            if hasattr(self, "on_press"):
                self.on_press(self)
            if event.key == _pygame.K_BACKSPACE:
                self.remove_char()
                self.start_quick_add(_pygame.K_BACKSPACE)
            elif event.key == _pygame.K_DELETE:
                if self.cursor_position < len(self.text):
                    self.register_undo({
                        "ori": self.text,
                        "pos": self.cursor_position,
                        "type": "delete"
                    })
                    self.text = self.text[:self.cursor_position] + self.text[self.cursor_position+1:]
                    self.check_bounds()
            elif event.key == _pygame.K_v and _pygame.key.get_pressed()[_pygame.K_LCTRL] and _pygame.scrap.get_init():
                self.register_undo({
                    "ori": self.text,
                    "pos": self.cursor_position,
                    "type": "char_add"
                })
                copied = get_clipboard_text()
                self.text = self.text[:self.cursor_position] + copied + self.text[self.cursor_position:]
                self.cursor_position += len(copied)
                self.check_bounds()
            elif event.key == _pygame.K_RETURN:
                self.focused = False
                self.exit_box(True)
            elif event.key == _pygame.K_LEFT:
                self.cursor_position -= 1 if self.cursor_position > 0 else 0
                if self.get_pixel_x() - self.scroll_x <= 0 and self.scroll_x > 0:
                    self.scroll_x -= self.font.size(self.text[self.cursor_position])[0]
            elif event.key == _pygame.K_RIGHT:
                self.cursor_position += 1 if self.cursor_position < len(self.text) else 0
                if self.get_pixel_x() - self.scroll_x >= self.size[0] and self.cursor_position < len(self.text):
                    self.scroll_x += self.font.size(self.text[self.cursor_position])[0] + self.text_offset_input
            elif event.key == _pygame.K_z and _pygame.key.get_pressed()[_pygame.K_LCTRL]:
                self.undo_stack.undo()
                self.check_bounds()
            else: 
                if len(event.unicode) > 0 and event.unicode.isprintable():
                    self.add_char(event.unicode)
                    self.start_quick_add(event.unicode)
        
        if event.type == _pygame.KEYUP and self.focused and self.editable:
            if event.unicode == self._held_key_code:
                self.held_key = False
    
    def add_char(self, char: str) -> _Self:
        self.register_undo({
            "ori": self.text,
            "pos": self.cursor_position,
            "type": "char_add"
        })
        self.cursor_visible = True
        self.now = _time.time()
        self.text = self.text[:self.cursor_position] + char + self.text[self.cursor_position:]
        self.cursor_position += 1
        self.check_bounds()

        return self

    def get_pixel_x(self) -> int:
        return self.font.size(self.text[:self.cursor_position])[0]

    def draw(self, target_surface: _pygame.Surface=None) -> None:
        if self.hidden:
            if self.focused: self.exit_box()
            return
        if self.size[0] <= 0 or self.size[1] <= 0: return

        self.surface.fill(COLORS["TRANSPARENT"])
        self.surface.blit(self.cached_text_surface, (-self.scroll_x, self.surface.get_height()/2-self.cached_text_surface.get_height()/2))

        if self.focused and self.held_key:
            if _time.time() - self._held_key_tick > 0.65:
                if self._held_key_code == _pygame.K_BACKSPACE:
                    self.remove_char()
                else:
                    self.add_char(self._held_key_code)

        if self.focused and self.cursor_visible:
            x_pos = self.get_pixel_x()

            _pygame.draw.line(self.surface, COLORS["WHITE"], 
                            (x_pos-self.scroll_x, self.surface.get_height()/6), 
                            (x_pos-self.scroll_x, self.surface.get_height()-self.surface.get_height()/4), 2
                            )
                
        if _time.time() - self.now > 0.5 and self.focused:
            self.now = _time.time()
            self.cursor_visible = not self.cursor_visible
        elif not self.focused:
            if not self.cursor_visible:
                self.cursor_visible = True

        self.draw_elements(self.surface)
        
        if self.stroke_thickness > 0: 
            _pygame.draw.rect(target_surface, self.stroke_color, self.get_stroke_rect(), border_radius=self.get_border_radius())

        pos = (self.position[0], self.position[1]-self.get_menu_scroll())

        _pygame.draw.rect(target_surface, self.background_color if not self.focused else self.focused_color, (*pos, *self.size), border_radius=self.get_border_radius(0))
        target_surface.blit(self.surface, pos)    

class MultiLineTextBox(UIElement):
    '''
        A multi line supported text entry. This should be used in multi line user text entry.
    '''
    def __init__(self, parent: UIElement=None, size: Coordinate=(200, 100), position: Coordinate=(0, 0), 
        background_color: tuple[int, int, int]=None, stroke_thickness: int=4, stroke_color: tuple[int, int, int]=COLORS["BLACK"], 
        children: list[UIElement]=None, name: str="UIElement", text: list[str]=None, border_radius: int=0,
    ):
        super().__init__(parent=parent, size=size, position=position, background_color=background_color, stroke_thickness=stroke_thickness, stroke_color=stroke_color, 
                        children=children, name=name, border_radius=border_radius)
        self._lines = text or ["Hello world!"]
        self.undo_stack = _Stack([])
        self.cursor_colum = 0
        self.cursor_line = 0
        self.font = _global_font
        self.text_scroll = 0
        self.focused = False
        self.cursor_visible = True
        self.cursor_enabled = True
        self.editable = True
        self.line_gap = 15
        self.cur_time = _time.time()
        self.max_lines = 100
        self.max_scroll = 300
        self.scrollbar_size = (6, 40)

        self.held_key = False
        self._held_key_tick = _time.time()

        def undo(context: str, value: _Any):
            self.cursor_line = value[0]
            self.current_line = value[2]
            self.cursor_colum = value[1]
        
        self.undo_stack.on_undo = undo
    
    def on_mouse_hover(self, entering, mouse_enter_pos):
        if self.hidden:
            return
        if not self.editable:
            return
        _pygame.mouse.set_cursor(_pygame.SYSTEM_CURSOR_IBEAM if entering else _pygame.SYSTEM_CURSOR_ARROW)

    def word_formatter(self, word: str, font: _pygame.font.Font, word_size: Coordinate) -> _pygame.Surface:
        '''
            This is a formatter/embedder. Its meant to give special control on how words are rendered inside the textbox. 
            This is meant to be overriden and currently just renders plain white text.
        '''
        return font.render(word, True, COLORS["WHITE"])

    def get_editor_text(self) -> str:
        result = ""
        for line in self.lines:
            if len(line) <= 0:
                result += "\n"
            else:
                for char in line:
                    result += char
        
        return result

    @property
    def lines(self) -> list[str]:
        return self._lines
    
    @lines.setter
    def lines(self, value: str):
        if isinstance(value, str):
            self._lines = value.split("\n")
        elif isinstance(value, list):
            self._lines = value


    @property
    def current_line(self):
        return self.lines[self.cursor_line]
    
    @current_line.setter
    def current_line(self, value: str):
        self.lines[self.cursor_line] = value

    def before_cursor(self) -> str:
        return self.current_line[:self.cursor_colum]
    
    def after_cursor(self) -> str:
        return self.current_line[self.cursor_colum:]

    def add_char_at_pos(self, char: str) -> _Self:
        self.lines[self.cursor_line] = self.before_cursor() + char + self.after_cursor()
        self.cursor_colum += 1
        return self

    def remove_char_at_pos(self) -> _Self:
        if self.cursor_colum > 0:
            self.lines[self.cursor_line] = self.current_line[:self.cursor_colum-1] + self.after_cursor()
            self.cursor_colum -= 1
        elif self.cursor_line > 0:
            now = self.after_cursor()
            self.lines.remove(now)
            self.cursor_line -= 1
            self.cursor_colum = len(self.current_line)
            self.lines[self.cursor_line] = self.current_line + now
        
        return self

    def add_line(self) -> _Self:
        this = self.after_cursor()
        this_2 = self.before_cursor()

        self.lines[self.cursor_line] = this
        self.lines.insert(self.cursor_line, this_2)
        self.cursor_line += 1
        if len(this_2) > len(self.current_line):
            self.cursor_colum = 0
        
        return self

    def set_cursor_position(self, mouse_pos: Coordinate) -> _Self:
        mouse_pos = (mouse_pos[0] - self.position[0], mouse_pos[1] - self.position[1])
        self.cursor_line = min(len(self.lines)-1, (mouse_pos[1] + self.text_scroll) // self.line_gap)

        for x in range(len(self.current_line)):
            if self.font.size(self.current_line[:x])[0] > mouse_pos[0]:
                self.cursor_colum = x
                break
            else:
                self.cursor_colum = x
        else:
            self.cursor_colum = len(self.current_line)
        
        return self

    def add_history(self) -> _Self:
        self.undo_stack.insert(( self.cursor_line,self.cursor_colum, self.lines[self.cursor_line] ))
        return self

    def handle_event(self, event: pygame_event_type):
        self.handle_event_components(event)
        if event.type == _pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.hidden:
            if not hasattr(self, "on_selected"):
                result = self.mouse_hovering
            else:
                result = self.on_selected(self, event, self.local_mouse_position if self.parent else event.pos)
            
            if not result and self.focused:
                if hasattr(self, "on_focus_lost"):
                    self.on_focus_lost(self.get_editor_text())

            self.focused = result
            if self.focused:
                self.set_cursor_position(self.local_mouse_position)
        
        if event.type == _pygame.MOUSEWHEEL and self.focused and self.mouse_hovering:
            self.text_scroll += event.y*-5
            if self.text_scroll < 0:
                self.text_scroll = 0
        
        if event.type == _pygame.KEYDOWN and self.focused and self.editable:
            self.max_scroll = self.font.size(self.get_editor_text())[1]

            self.cursor_visible = True
            self.cur_time = _time.time()
            if event.key == _pygame.K_BACKSPACE:
                self.add_history()
                self.remove_char_at_pos()
                self.start_held_key_press(_pygame.K_BACKSPACE)

            elif event.key == _pygame.K_LEFT:
                if self.cursor_colum > 0:
                    self.cursor_colum -= 1
                elif self.cursor_line > 0:
                    self.cursor_line -= 1
                    self.cursor_colum = len(self.current_line)
            elif event.key == _pygame.K_RIGHT:
                if self.cursor_colum < len(self.current_line):
                    self.cursor_colum += 1
                elif self.cursor_line < len(self.lines) - 1:
                    this = self.current_line
                    self.cursor_line += 1
                    self.cursor_colum = 0
            elif event.key == _pygame.K_RETURN:
                self.add_line()
                self.start_held_key_press(_pygame.K_RETURN)
            elif event.key == _pygame.K_UP:
                if self.cursor_line > 0:
                    self.cursor_line -= 1
            elif event.key == _pygame.K_DOWN:
                if self.cursor_line < len(self.lines) - 1:
                    self.cursor_line += 1
            elif event.key == _pygame.K_v and _pygame.key.get_pressed()[_pygame.K_LCTRL] and _pygame.scrap.get_init():
                self.add_history()
                copied = get_clipboard_text()
                self.lines[self.cursor_line] = self.before_cursor() + copied + self.after_cursor()
                self.cursor_colum += len(copied)
            elif event.key == _pygame.K_z and _pygame.key.get_pressed()[_pygame.K_LCTRL]:
                self.undo_stack.undo()
            elif event.key == _pygame.K_TAB:
                self.add_history()
                self.add_char_at_pos("    ")    
            else:
                if len(event.unicode) > 0 and event.unicode.isprintable():
                    self.add_history()
                    self.add_char_at_pos(event.unicode)
                    self.start_held_key_press(event.unicode)

        if event.type == _pygame.KEYUP and self.focused and self.editable:
            if event.unicode == self._held_key_code:
                self.held_key = False

    def start_held_key_press(self, char: str | int) -> _Self:
        self.held_key = True
        self._held_key_code = char
        self._held_key_tick = _time.time()

        return self

    def draw(self, target_surface: _pygame.Surface):
        if len(self.lines) <= 0: self.lines = [""]
        self.surface.fill(COLORS["TRANSPARENT"])

        self.max_scroll = self.surface.get_height()-1

        if self.focused and self.held_key:
            if _time.time() - self._held_key_tick > 0.65:
                if self._held_key_code == _pygame.K_BACKSPACE:
                    self.remove_char_at_pos()
                elif self._held_key_code == _pygame.K_RETURN:
                    self.add_line()
                else:
                    self.add_char_at_pos(self._held_key_code)

        _pygame.draw.rect(self.surface, COLORS["GRAY"], 
                            self._get_scrollbar_rect(self.text_scroll, self.max_scroll, self.scrollbar_size))

        y = 0
        for i, line in enumerate(self.lines):
            x = 0
            for word in line.split(" "):
                text_surface = self.word_formatter(word, self.font, self.font.size(word))
                self.surface.blit(text_surface, (x, y-self.text_scroll))
                x += text_surface.get_width() + self.font.size(" ")[0]
            
            y += self.line_gap

        if _time.time() - self.cur_time > 0.6 and self.cursor_enabled and self.focused:
            self.cur_time = _time.time()
            self.cursor_visible = not self.cursor_visible
        
        if self.max_scroll > 0 and self.max_scroll > self.surface.get_height():
            self._draw_scrollbar(self.text_scroll, self.max_scroll, self.scrollbar_size)

        if self.cursor_visible and self.cursor_enabled and self.focused:
            x = self.font.size(self.current_line[:self.cursor_colum])[0]
            y = (self.cursor_line * self.line_gap) - self.text_scroll

            _pygame.draw.line(
                self.surface, 
                COLORS["WHITE"], 
                (x, y),
                (x, y+self.line_gap),
            )

            if x > self.surface.get_width():
                self.add_line()

        pos = (self.position[0], self.position[1]-self.get_menu_scroll())

        if self.stroke_thickness > 0: _pygame.draw.rect(target_surface, self.stroke_color, self.get_stroke_rect(), border_radius=self.get_border_radius())
        _pygame.draw.rect(target_surface, self.background_color, (*pos, *self.size), border_radius=self.get_border_radius(0))
        target_surface.blit(self.surface, pos)

class Bar(UIElement):
    '''
        A resizable bar element. This should be used ethier as a slider or as a progress bar.
    '''
    def __init__(self, parent: UIElement=None, size: Coordinate=(150, 25), position: Coordinate=(0, 0), 
                 background_color: tuple[int, int, int]=None, foreground_color: tuple[int, int, int]=COLORS["WHITE"], stroke_thickness: int=4, 
                 stroke_color=COLORS["BLACK"], children: list[UIElement]=None, name: str="Bar", border_radius: int=0):
        super().__init__(parent, size, position, background_color, stroke_thickness, stroke_color, children=children, name=name, border_radius=border_radius)
        self.bar_percent = 0.5
        self.resize_click_range = 30
        self.foreground_color = foreground_color
        self.resizable = True
        self.resizing = False

    def set_percent(self, new_percent: float) -> _Self:
        '''
            Sets the bar percent.
        '''
        self.bar_percent = new_percent
        return self

    def handle_event(self, event: pygame_event_type) -> None:
        self.handle_event_elements(event)
        if event.type == _pygame.MOUSEBUTTONDOWN and event.button == 1 and self.mouse_over_parent() and self.resizable:
            pos = self.local_mouse_position if self.parent else _pygame.mouse.get_pos()
            
            handle_x = self.size[0] * self.bar_percent

            if (handle_x - self.resize_click_range <= pos[0]-self.position[0] <= handle_x) and self.mouse_hovering:
                self.resizing = True
        elif event.type == _pygame.MOUSEBUTTONUP and event.button == 1:
            self.resizing = False
        elif event.type == _pygame.MOUSEMOTION and self.resizing:
            relative_x = _pygame.mouse.get_pos()[0] - self.get_screen_position()[0]
            self.bar_percent = max(0.0, min(1.0, relative_x / self.size[0]))

    def draw(self, target_surface: _pygame.Surface=None):
        if self.size[0] <= 0 or self.size[1] <= 0: return
        final_pos = (self.position[0], self.position[1]-self.get_menu_scroll())
        self.surface.fill(COLORS["TRANSPARENT"])

        _pygame.draw.rect(self.surface, self.foreground_color, (0, 0, self.size[0]*self.bar_percent, self.size[1]), border_radius=self.get_border_radius())
        if self.stroke_thickness > 0: _pygame.draw.rect(target_surface, self.stroke_color, self.get_stroke_rect(), border_radius=self.get_border_radius())
        _pygame.draw.rect(target_surface, self.background_color, (*final_pos, *self.size), border_radius=self.get_border_radius(0))
        target_surface.blit(self.surface, final_pos)

class Menu(UIElement): 
    '''
        A scrollable menu element. This should be used to contain other elements and be scrollable.
    '''
    def __init__(self, position: Coordinate=(0, 0), size: Coordinate=(350, 200), children: list[UIElement]=None, 
                 stroke_thickness: int=3, background_color: tuple[int, int, int]=None, 
                 parent: UIElement=None, name: str="ScrollableMenu", max_scroll: int=0, border_radius: int=0, scroll_speed: int=10):
        super().__init__(parent, size, position, background_color or COLORS["DARKER-GRAY"], name=name, children=children, border_radius=border_radius)
        self.scroll_y = 0
        self.scrollable = True
        self.max_scroll = max_scroll
        self.layout = None
        self.scrollbar_size = (6, 40)
        self.textfont_draw = _pygame.font.SysFont("consolas", self.surface.get_height()-5)
        self.focused = False
        self.current_scrollbar_rect = None
        self.scrollbar_dragging = False
        self.scrollbar_offset = 0
        self.scroll_speed = scroll_speed
        self.scroll_velocity = 0
        self._scroll_decrement = self.scroll_speed/20
    
    def set_scrollable(self, enabled: bool) -> _Self:
        self.scrollable = enabled
        return self

    def set_max_scroll(self, new_max_scroll: int) -> _Self:
        self.max_scroll = new_max_scroll
        return self

    def update_max_scroll(self, offset: int=0) -> _Self:
        if not self.children:
            self.max_scroll = 0
            return self

        content_bottom = max(element.position[1] + element.size[1] for element in self.children if not element.hidden)
        self.max_scroll = max(0, content_bottom - self.size[1]) + offset

        return self
    
    def set_scroll_speed(self, new_scroll_speed: int) -> _Self:
        self.scroll_speed = new_scroll_speed
        return self

    def default(self) -> _Self:
        self.stroke_thickness = 0
        self.background_color = COLORS["TRANSPARENT"]
        self.stroke_color = COLORS["TRANSPARENT"]
        self.scroll_y = 0
        return self

    def get_layout_name(self) -> str:
        return self.layout.__class__.__name__

    def handle_event(self, event: pygame_event_type) -> None:
        self.handle_event_elements(event)

        if event.type == _pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.hidden and self.mouse_over_parent():
            local_p = self.local_mouse_position if self.parent else event.pos

            if not hasattr(self, "on_selected"):
                result = self.mouse_hovering
            else:
                result = self.on_selected(self, event, local_p)
            
            self.focused = result

            if self.focused and self.scrollable and self.max_scroll > 0:
                pos = _pygame.mouse.get_pos()
                self.scrollbar_dragging = self.current_scrollbar_rect.collidepoint(pos)
                self.scrollbar_offset = pos[1]-self.current_scrollbar_rect.y

        elif event.type == _pygame.MOUSEWHEEL and self.focused and self.scrollable and self.mouse_hovering:
            for v in self.children:
                if isinstance(v, Menu) and v.focused and v.parent is self:
                    return
                elif isinstance(v, MultiLineTextBox) and v.focused and v.parent is self:
                    return

            self.scroll_velocity = event.y*-self.scroll_speed

        elif event.type == _pygame.MOUSEBUTTONUP and self.scrollbar_dragging:
            self.scrollbar_dragging = False

        elif event.type == _pygame.MOUSEMOTION and self.scrollbar_dragging:
            self.scroll_velocity = 0
            percent = max(0, min(1, (self.local_mouse_position[1]-self.position[1]-self.scrollbar_offset-
            (self.title_bar_height if isinstance(self, SubWindow) else 0)) / 
                (self.surface.get_height() - self.scrollbar_size[1]) 
            ))

            self.scroll_y = (percent * self.max_scroll)

    def apply_layout(self, layout_class: type, *args: tuple[_Any], **kwargs: dict[str, _Any]) -> _Self:
        layout = layout_class(self, *args, **kwargs)
        self.layout = layout
        return self

    def draw_scrollbar_rect(self, target_surface: _pygame.Surface) -> None:
        '''
            This should be used in any practical sense. This is meant for testing on screen position.
        '''
        _pygame.draw.rect(target_surface, COLORS["WHITE"], self.current_scrollbar_rect)

    def draw(self, target_surface: _pygame.Surface=None) -> None:
        if self.hidden: return
        if self.size[0] <= 0 or self.size[1] <= 0: return

        if self.scroll_velocity > 0:
            self.scroll_velocity = max(0, self.scroll_velocity - self._scroll_decrement)
        elif self.scroll_velocity < 0:
            self.scroll_velocity = min(0, self.scroll_velocity + self._scroll_decrement)
        
        self.scroll_y += self.scroll_velocity

        self.scroll_y = min(self.max_scroll, max(0, self.scroll_y))

        final_pos = (self.position[0], self.position[1]-self.get_menu_scroll())
        
        if self.layout is not None and len(self.children) > 0:
            self.layout.update()

        self.surface.fill(COLORS["TRANSPARENT"])

        self.draw_elements(self.surface)
        
        if self.scrollable and self.max_scroll > 0:
            scrollbar_rect = self._get_scrollbar_rect(self.scroll_y, self.max_scroll, self.scrollbar_size)

            _pygame.draw.rect(self.surface, COLORS["GRAY"], scrollbar_rect)

            screen_position = self.get_screen_position()
            scrollbar_rect = _pygame.Rect(
                screen_position[0] + self.size[0]-self.scrollbar_size[0],
                screen_position[1]+scrollbar_rect[1],
                *self.scrollbar_size
            )
            self.current_scrollbar_rect = scrollbar_rect

        if self.stroke_thickness > 0: _pygame.draw.rect(target_surface, self.stroke_color, self.get_stroke_rect(), border_radius=self.get_border_radius())
        _pygame.draw.rect(target_surface, self.background_color, (*final_pos, *self.size), border_radius=self.get_border_radius(0))
        target_surface.blit(self.surface, final_pos)

class CheckBox(TextButton):
    '''
        A check button which holds a True or False value. This should be used for toggleable values from the user.
    '''
    def __init__(self, text: str="Enabled", position: Coordinate=(0, 0), parent: UIElement=None, checked: bool=False, 
                 on_flip: _Callable=lambda enabled: print(enabled), size: Coordinate=(160, 30), border_radius: int=0):
        def flip() -> None: 
            self._checked = not self._checked
            if hasattr(self, "on_flip") and callable(self.on_flip):
                self.on_flip(self.get_value())

        super().__init__(text, position, size=size, parent=parent, clickable=True, action=flip, background_color=COLORS["LIGHTER-GRAY"], border_radius=border_radius)

        def should_click(mouse_pos: Coordinate):
            return self.get_checkbox_rect().collidepoint(mouse_pos)

        self._checked = checked
        self.stroke_thickness = 2
        self.on_flip = on_flip
        height = self.size[1]-15
        self.check_box_rect = _pygame.Rect(5, self.size[1]/2-height/2, self.size[0]*0.10, height)
        self.components[0].should_click = should_click

    def get_value(self) -> bool:
        return self._checked

    def get_checkbox_rect(self) -> _pygame.Rect:
        return _pygame.Rect(
            self.check_box_rect.x + self.screen_position[0],
            self.check_box_rect.y + self.screen_position[1],
            *self.check_box_rect.size
        )

    def handle_event(self, event: pygame_event_type) -> None:
        '''
            Overrides the normal clickable component to make sure the user clicked on the checkbox.
        '''
        self.handle_event_components(event)

    def draw(self, target_surface: _pygame.Surface) -> None:
        self.surface.fill(COLORS["TRANSPARENT"])
        final_pos = (self.position[0], self.position[1]-self.get_menu_scroll())

        box_color = COLORS["GREEN"] if self._checked else COLORS["RED"]

        _pygame.draw.rect(self.surface, box_color, self.check_box_rect)
        self.surface.blit(self.cached_text_surface, (self.size[0]*0.18, self.size[1]/2-self.cached_text_surface.get_height()/2))

        if self.stroke_thickness > 0: _pygame.draw.rect(target_surface, self.stroke_color, self.get_stroke_rect(), border_radius=self.get_border_radius())
        _pygame.draw.rect(target_surface, self.background_color, (*final_pos, *self.size), border_radius=self.get_border_radius(0))
        target_surface.blit(self.surface, final_pos)

class SubWindow(Menu):
    '''
        A draggable menu. This should be used to hold other elements the user can move around willingly.\n
        **NOTE: Scrollbar visual may clip out of the window slightly.**
    '''
    def __init__(self, position: Coordinate=(0, 0), size: Coordinate=(350, 200), children: list[UIElement]=None, 
                stroke_thickness: int=3, background_color: tuple[int, int, int]=None, parent: UIElement=None, name: str="ScrollableMenu", 
                max_scroll: int=0, title: str="Sub Window!", title_bar_height: int=25, border_radius: int=0, title_text_color: tuple[int, int, int]=COLORS["WHITE"],
                title_bar_color: tuple[int, int, int]=COLORS["LIGHTER-GRAY"], title_bar_font: _pygame.font.Font | None=None):
        super().__init__(position, size, children, stroke_thickness, background_color, parent, name, max_scroll, border_radius=border_radius)
        self.title_bar_height = title_bar_height
        self.sub_surface = _pygame.Surface((self.size[0], self.size[1]-self.title_bar_height), _pygame.SRCALPHA)
        self.titlebar_surface = _pygame.Surface((self.size[0], self.title_bar_height), _pygame.SRCALPHA)
        self.title_bar_text_font = title_bar_font or _global_font

        self._title = title
        self._cached_text_surface = self.title_bar_text_font.render(self.title, True, (255, 255, 255))
        self.title_bar_color = title_bar_color

        self._title_text_color = title_text_color

        self.components = [
            DragComponent(self)
        ]

        self.components[0].should_start_drag = lambda pos: self.titlebar_surface.get_rect(topleft=self.screen_position).collidepoint(pos)
        self._border_radius = self.border_radius

        self._close_button = self.title_bar_text_font.render("X", True, COLORS["WHITE"])
        self._close_button_position = (self.size[0] - self._close_button.get_width()-20, 5)

        self.minimized = False


    def update_title_surface(self):
        self._cached_text_surface = self.title_bar_text_font.render(self._title, True, self._title_text_color)

    @property
    def size(self):
        return self._size
    
    @size.setter
    def size(self, new_size: Coordinate):
        self.resize(new_size)

    @property
    def title_text_color(self):
        return self._title_text_color
    
    @title_text_color.setter
    def title_text_color(self, value: tuple[int, int, int]):
        self._title_text_color = value
        self.update_title_surface()

    @property
    def title(self):
        return self._title
    
    @title.setter
    def title(self, value: str):
        self._title = value
        self.update_title_surface()

    @property
    def border_radius(self):
        return self._border_radius
    
    @border_radius.setter
    def border_radius(self, value: int):
        self._border_radius = value

        for child in self.children:
            if isinstance(child, Menu) and child.size == self.size:
                child.border_radius = self.border_radius

    def resize(self, new_size: Coordinate) -> _Self:
        self.sub_surface = _pygame.Surface((new_size[0], max(self.title_bar_height, new_size[1]-self.title_bar_height)), _pygame.SRCALPHA)
        self.titlebar_surface = _pygame.Surface((new_size[0], self.title_bar_height), _pygame.SRCALPHA)

        self._size = new_size
        self.update_surface()

    def handle_event(self, event: pygame_event_type):
        super().handle_event(event)

        if event.type == _pygame.MOUSEBUTTONDOWN and self.focused:
            final_position = (
                self.screen_position[0] + self._close_button_position[0],
                self.screen_position[1] + self._close_button_position[1]
            )

            if self._close_button.get_rect(topleft=final_position).collidepoint(_pygame.mouse.get_pos()):
                self.destroy()


    def draw(self, target_surface: _pygame.Surface=None) -> None:
        if self.hidden: return
        if self.size[0] <= 0 or self.size[1] <= 0: return

        final_pos = (self.position[0], self.position[1]-self.get_menu_scroll())
        
        if self.layout is not None and len(self.children) > 0:
            self.layout.update()

        self.surface.fill(COLORS["TRANSPARENT"])
        self.sub_surface.fill(COLORS["TRANSPARENT"])
        self.titlebar_surface.fill(COLORS["TRANSPARENT"])

        self.children.sort(key=lambda a: a.Z)

        self.draw_elements(self.sub_surface)
        self.titlebar_surface.blit(self._cached_text_surface, (5, self.title_bar_height/2-self._cached_text_surface.get_height()/2))

        if self.scrollable and self.max_scroll > 0:
            scrollbar_rect = self._get_scrollbar_rect(self.scroll_y, self.max_scroll, self.scrollbar_size)

            screen_position = self.screen_position
            scrollbar_rect = _pygame.Rect(
                screen_position[0] + self.size[0]-self.scrollbar_size[0],
                screen_position[1]+scrollbar_rect[1]+self.title_bar_height,
                *self.scrollbar_size
            )

            self.current_scrollbar_rect = scrollbar_rect

            _pygame.draw.rect(self.sub_surface, COLORS["LIGHTER-GRAY"], scrollbar_rect)

        if self.stroke_thickness > 0:
            stroke_rect = self.get_stroke_rect()
            _pygame.draw.rect(target_surface, self.stroke_color, (stroke_rect[0], stroke_rect[1], stroke_rect[2], 
                                                                  stroke_rect[3]
                                                                  ), border_radius=self.get_border_radius())
        _pygame.draw.rect(self.surface, self.title_bar_color, 
                        ((0, 0), (self.size[0], self.titlebar_surface.get_height())), border_top_left_radius=self.get_border_radius(), 
                        border_top_right_radius=self.get_border_radius())

        self.surface.blit(self.titlebar_surface, (0, 0))
        
        _pygame.draw.rect(self.surface, self.background_color, (0, self.title_bar_height, *self.sub_surface.get_size()), border_bottom_left_radius=self.get_border_radius(), 
                        border_bottom_right_radius=self.get_border_radius())

        self.surface.blit(self.sub_surface, (0, self.title_bar_height))

        self.surface.blit(self._close_button, self._close_button_position)

        _pygame.draw.line(self.surface, self.stroke_color, (0, self.title_bar_height), (self.size[0], self.title_bar_height), 3)
        target_surface.blit(self.surface, final_pos)

# ----------------------------
# LAYOUTS
# ----------------------------

class VerticalLayout(MenuLayout):
    '''
        Forms menu children in a downward chart formation based off mode enums.
    '''
    def __init__(self, parent: Menu, item_gap: int=25, horizontal_padding: int=5, vertical_padding: int=5, horizontal_mode: LayoutAlignment=LayoutAlignment.left, vertical_mode: LayoutAlignment=LayoutAlignment.up):
        super().__init__(parent)
        self.horizontal_mode = horizontal_mode
        self.vertical_mode = vertical_mode
        self.item_gap = item_gap
        self.horizontal_padding = horizontal_padding
        self.vertical_padding = vertical_padding
    
    def disable(self) -> _Self:
        super().switch_enabled(False)
        for i, element in enumerate(self.parent.children):
            if element.position != self.origin_pos_elements[i]:
                element.position = self.origin_pos_elements[i]
        
        return self

    def base_update(self) -> None:
        y = 0

        self.parent.update_max_scroll()

        if self.vertical_mode == LayoutAlignment.up:
            y = self.vertical_padding
        elif self.vertical_mode == LayoutAlignment.center:
            y = self.parent.size[1]/2
        elif self.vertical_mode == LayoutAlignment.down:
            y = self.parent.size[1]

        for element in self.parent.children:
            if not isinstance(element, UIElement): continue
            if element.hidden: continue

            new_pos = (element.position[0], y)
            if self.vertical_mode == LayoutAlignment.down:
                new_pos = (new_pos[0], y-element.size[1])
            elif self.vertical_mode == LayoutAlignment.center:
                new_pos = (new_pos[0], new_pos[1]-element.size[1]/2)
            elif self.vertical_mode == LayoutAlignment.up:
                new_pos = (new_pos[0], y)

            if self.horizontal_mode == LayoutAlignment.left:
                new_pos = (self.horizontal_padding, y)
            elif self.horizontal_mode == LayoutAlignment.center:
                new_pos = (self.parent.size[0]/2-element.size[0]/2, y)
            elif self.horizontal_mode == LayoutAlignment.right:
                new_pos = (self.parent.size[0]-element.size[0]-self.parent.scrollbar_size[0]-self.horizontal_padding, y)
            
            element.position = new_pos
            if self.vertical_mode == LayoutAlignment.down:
                y -= self.item_gap + element.surface.get_height()
            else:
                y += self.item_gap + element.surface.get_height()

class FlowLayout(MenuLayout):
    '''
        Forms menu children in a formation left to right from top to bottom based of if its off the menu size.
    '''
    def __init__(self, parent: Menu, row_gap: int=30, vertical_item_gap: int=25, horizontal_item_gap: int=30):
        super().__init__(parent)
        self.horizontal_item_gap = horizontal_item_gap
        self.vertical_item_gap = vertical_item_gap
        self.row_gap = row_gap

    def base_update(self) -> None:
        x = self.horizontal_padding
        y = self.vertical_padding

        self.parent.update_max_scroll()

        for element in self.parent.children:
            if not isinstance(element, UIElement): continue
            if element.hidden: continue

            new_pos = (element.position[0], element.position[1])

            if x > self.parent.surface.get_width():
                y += self.row_gap + self.vertical_item_gap
                x = self.horizontal_padding

            element.position = (x, y)

            if element.position[0] + element.size[0] > self.parent.surface.get_width():
                y += self.row_gap + self.vertical_item_gap + element.size[1]
                x = self.horizontal_padding
                element.position = (x, y)

            x += element.surface.get_width() + self.horizontal_item_gap

# ----------------------------
# HELPERS
# ----------------------------

def get_elements_tree(root_element: UIElement) -> list[tuple[UIElement, int]]:
    '''
        Returns a list of all ui elements starting from the root element in a tree formation using depth.
    '''
    result = []

    def walk(element: UIElement, depth: int = 0):
        if not isinstance(element, Canvas):
            result.append((element, depth))

            for child in element.children:
                walk(child, depth + 1)
        else:
            for element in element.layer:
                walk(element, depth)

    walk(root_element)

    return result

def draw_text(text: str, position: Coordinate, color: tuple[int, int, int], 
              surface: _pygame.Surface, font: _pygame.font.Font=None) -> None:
    '''
        Draws text onto a surface with all the provided arguments. 
        Suggested to create a font outside of loop as it creates a new font for each call of this.
    '''
    if font is None: font = _global_font
    surface.blit(font.render(text, True, color), position)

def draw_tree_view(tree_view: list[tuple[UIElement, int]], surface: _pygame.Surface, font: _pygame.font.Font=None, text_offset=(5, 10)) -> None:
    '''
        Goes through a list of elements meant to be from get_elements_tree() and draws them onto the surface.
        Useful for debugging where elements are in a UI hierarchy.
    '''
    y = text_offset[1]
    for entry in tree_view:
        text = f"{entry[0].name}"
        text += f" ({entry[0].layout})" if isinstance(entry[0], Menu) and entry[0].layout is not None else ""
        
        draw_text(text, (text_offset[0]+entry[1]*25, y), COLORS["WHITE"], surface, font)
        y += 15

print(f"SparseGUI v1.2.4 (Python {_sys.version[0:7]}, pygame {_pygame.ver})")

# Defining what is imported if import * is used on this module
__all__: list[str] = [name for name, obj in globals().items() if name[0] != "_" or name.startswith("_")]
