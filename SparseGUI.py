
'''
    SparseGUI
    -
    
    Retained-mode UILibrary written in python 3.13.3 pygame 2.6.1. Allows for well running and comprehensive UI in pygame in a parent child 
    hierarchy without needing to manually drawn to surfaces. Allows for easier GUI work and has a built set of diverse GUI elements.\n
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
from uuid import uuid4 as _uuid4

# ----------------------------
# GLOBALS
# ----------------------------

Coordinate = tuple[int, int] # Coordinate

_global_font = None # The global font used by the library as a placeholder for fonts not given to elements.
_command_key = _pygame.K_LCTRL

def command_key():
    '''
        The key used for textbox's special case features, such as pasting or copying.
    '''
    return _command_key

def init(global_font_name="consolas", global_font_size=15) -> bool:
    global _global_font
    
    if not _pygame.get_init():
        _pygame.init()

    _global_font = _pygame.font.SysFont(global_font_name, global_font_size)

    return True

def get_clipboard_text() -> str:
    return _pygame.scrap.get_text()

# Sets the clipboard text to the given text
def set_clipboard_text(text: str) -> None:
    _pygame.scrap.put_text(text)

# Changes the cursor hand based off a toggle for the arrow and hand.
def set_cursor_hand(enabled: bool) -> None:
    _pygame.mouse.set_cursor(_pygame.SYSTEM_CURSOR_HAND if enabled else _pygame.SYSTEM_CURSOR_ARROW)

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
        Determines where text goes inside elements on the X axis (TextButton are supported currently).
    '''
    left = 0
    middle = 1
    right = 2

class TextYAlignment(_Enum):
    '''
        Determines where text goes inside elements on the Y axis (TextButton are supported currently).
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
# DATA CLASSES
# ----------------------------

class VideoElementData:
    '''
        Video data given to a VideoElement for it to playback from.
    '''
    def __init__(self, frames: list[_pygame.Surface], frame_rate: int):
        self.frames = frames
        self.frame_rate = frame_rate

    def get_video_frame(self, frame: int) -> _pygame.Surface:
        return self.frames[min(frame, len(self.frames)-1)]

class Connection:
    '''
        Represents an active callback connected to an Event object
    '''
    def __init__(self, event: "Event", callback: _Callable):
        self._event = event
        self.connected = True
        self._callback = callback

    def disconnect(self):
        '''
            Disconencts the connection from its event.
        '''
        self.connected = False
        self._callback = None
        self._event._connections.remove(self)
        self._event = None

class Event:
    '''
        A collection of callbacks fired when something happens.
    '''
    def __init__(self):
        self._connections: list[Connection] = []

    def fire(self, *args, **kwargs) -> None:
        for connection in self._connections:
            connection._callback(*args, **kwargs)

    def _make_connection(self, callback: _Callable):
        con = Connection(self, callback)
        self._connections.append(con)
        return con

    def connect(self, callback: _Callable) -> Connection:
        '''
            Connects a new connection and returns it.
        '''
        return self._make_connection(callback)

    def once(self, callback: _Callable) -> Connection:
        '''
            Connects a new connection for one event call and returns it.
        '''
        con = Connection(self, None)

        def do(*args, **kwargs):
            callback(*args, **kwargs)
            con.disconnect()

        con._callback = do
        self._connections.append(con)

        return con

# ----------------------------
# CANVAS
# ----------------------------

class Canvas:
    '''
        The Canvas at which the top level widgets parented to.
    '''
    def __init__(self, screen_size: Coordinate=(500, 400), children: list["UIElement"] | None=None, 
                 fill_color: tuple[int, int, int]=COLORS["TRANSPARENT"], position: Coordinate | None=None):
        self.children = children or []
        self.hidden = False
        self.surface = _pygame.Surface(screen_size, _pygame.SRCALPHA)
        self.clip_root = True
        self.fill_color = fill_color
        self.position = position or (0, 0)

        if self.children:
            for element in children:
              element.parent = self

    def add_element(self, element):
        element.parent = self
        self.children.append(element)

    @property
    def size(self):
        return self.surface.get_size()
    
    @size.setter
    def size(self, value: Coordinate):
        self.surface = _pygame.Surface(value, _pygame.SRCALPHA)

    def destroy(self):
        '''
            Destroys the Canvas and its children.
        '''

        self.hidden = True
        self.fill_color = COLORS["TRANSPARENT"]
        
        for element in self.children:
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
        
        for element in self.children:
            walk(element)
        
        return results

    def any_gui_active(self) -> tuple[bool, "UIElement"]:
        '''
            Returns if any GUI is currently active. If so then returns a tuple of True and the element.
        '''
        stop = False
        element = None
        def walk(item: UIElement):
            nonlocal stop, element

            if hasattr(item, "focused") and item.focused and not stop:
                stop = True
                element = item
                
                if not stop:
                    for child in item.children:
                        walk(child)
        
        for child in self.children:
            walk(child)

        return stop, element

    def get_size(self) -> Coordinate:
        return self.surface.get_size()

    def handle_event(self, event: _pygame.event.Event):
        '''
            Handles the element events. This does nothing is the mouse isnt actively over the window surface.
        '''
        if not self.surface.get_rect(topleft=self.position).collidepoint(_pygame.mouse.get_pos()):
            return
        
        for element in self.children:
            if element.hidden: continue

            element.handle_event(event)

    def update(self, dt: float):
        '''
            Updates current elements.
        '''
        if self.hidden:
            return
        
        for element in self.children:
            element.update(dt)

    def draw(self, surface: _pygame.Surface):
        '''
            Draws current elements.
        '''
        if self.hidden: 
            return

        self.surface.fill(COLORS["TRANSPARENT"])

        self.children.sort(key=lambda a: a.Z)

        for element in self.children:
            if element.hidden: 
                continue

            element.draw(self.surface)

        surface.blit(self.surface, self.position)

# ----------------------------
# BASE CLASSES
# ----------------------------

class UIElement:
    '''
        The base class of a UI element.\n
    '''
    def __init__(self, 
                 parent: _Self | Canvas=None, size: Coordinate=(100, 50), position: Coordinate=(0, 0), 
                 background_color: tuple[int, int, int]=None, background_transparency: float=1, stroke_thickness: int=4, stroke_transparency: float=1, 
                 stroke_color: tuple[int, int, int] | None=None, children: list["UIElement"]=None, border_radius: int=0, name: str="UIElement"):
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
        self.stroke_color = stroke_color or COLORS["BLACK"]
        self.name = name
        self.screen_position = (0, 0)
        self.local_mouse_position = (0, 0)
        self.mouse_hovering = False
        self._active_tweens: list[_Tween] = []
        self.background_transparency = background_transparency
        self.stroke_transparency = stroke_transparency
        self.surface_transparency = 1
        self._watchable_properties: list[tuple[str, _Any]] = []

        self.Z = 1
        self.border_radius = border_radius
        self.sync_mouse = True

        self._register_watch_property("size")
        self._register_watch_property("position")
        self.on_property_changed = Event()
        self.on_mouse_hover = Event()

        for v in self.children:
            v.parent = self

    def get_point_offset(self) -> tuple[float | int, float | int]:
        ''' This is a overider for a custom offset to be given. '''
        return (0, 0)
    
    def _get_point_offset(self) -> tuple[float | int, float | int]:
        ''' This is a overider for a custom offset to be given. This is ued internally '''
        return (0, 0)
    
    def transform_point_to_local_space(self, point: Coordinate) -> Coordinate:
        '''
            Transforms the given point to the local space of the parent element. 
        '''
        selected = self.parent
        offset = self.get_point_offset()
        offset_2 = self._get_point_offset()

        while selected:
            point = (
                point[0] - selected.position[0] - offset[0] - offset_2[0],
                point[1] - selected.position[1] + (selected.scroll_y if isinstance(selected, Menu) else 0) - (selected.title_bar_height if isinstance(selected, SubWindow) else 0) - offset[1] - offset_2[0]
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

    def add_component(self, componet_type, *args, **kwargs) -> tuple[_Self, _Any]:
        '''
            This adds a componet (UIComponent) to the element. Returns self and the component instance made.
        '''
        componet_ins = componet_type(self, *args, **kwargs)
        componet_ins.init()

        self.components.append(componet_ins)
        return self, componet_ins

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

    def handle_event_components(self, event: _pygame.event.Event):
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
            self.position[0] / self.parent.size[0],
            self.position[1] / self.parent.size[1]
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

    def _get_scrollbar_rect(self, scroll_y: float, max_scroll: float, scrollbar_width: int) -> tuple:
        height = self.surface.get_height()
        content_height = height + max_scroll

        min_thumb = 0
        thumb_height = max(min_thumb, height * (height / content_height)) if content_height > 0 else height
        thumb_height = min(thumb_height, height)

        try:
            scroll_percent = max(0, min(scroll_y / max_scroll, 1))
        except ZeroDivisionError:
            scroll_percent = 0

        thumb_y = scroll_percent * (height - thumb_height)

        return (
            self.surface.get_width() - scrollbar_width,
            thumb_y,
            scrollbar_width,
            thumb_height,
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
            self.parent.children.remove(self)
            
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

        if duration < 0:
            raise ValueError(f"Provide duration larger than 0")

        def setter(v: Coordinate):
            self.position = v
        
        self._active_tweens.append(_Tween(self.position, target_position, setter, duration, on_end))
        return self

    def tween_size(self, target_size: Coordinate, duration: float=0.2, on_end: _Callable[[], None]=None) -> _Self:
        '''
            Tweens the elements size to the target size over the duration.
        '''

        if duration < 0:
            raise ValueError(f"Provide duration larger than 0")
        
        def setter(v: Coordinate):
            self.size = v
        
        self._active_tweens.append(_Tween(self.size, target_size, setter, duration, on_end))
        return self

    def add_child(self, child: "UIElement") -> _Self:
        ''' Adds a child to the element. '''

        if not isinstance(child, UIElement):
            raise ValueError(f"Type of child {child} is not type of base class {UIElement}")

        self.children.append(child)
        child.parent = self

        return self
    
    def remove_child(self, child: _Self) -> _Self:
        ''' Removes a child from the element. This doesnt have to be the assigned type and can be any child.'''

        if not isinstance(child, UIElement):
            raise ValueError(f"Type of child {child} is not type of base class {UIElement}")

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
        if not self.parent:
            return True

        current = self.parent

        for child in self.children:
            if child.mouse_hovering:
                return False

        while current:
            if isinstance(current, Canvas):
                rect = current.surface.get_rect(topleft=current.position)
            else:
                rect = current.surface.get_rect(topleft=current.screen_position)

            if not rect.collidepoint(_pygame.mouse.get_pos()):
                return False

            current = current.parent if hasattr(current, "parent") else None

        return True
    
    def mouse_over_element(self) -> bool:
        '''
            Returns wether the mouse is over the element based off screen position.
        '''
        result = True
        current = self.parent

        while current and result:
            items = current.children

            for element in items:
                if element is self:
                    continue

                if not element.hidden:
                    if element.mouse_hovering and element.Z > self.Z:
                        result = False
                    elif element.mouse_hovering and element.Z == self.Z and self in items and items.index(element) > items.index(self):
                        # ^ This branch is used for when the elements share a Z layer, in this case 
                        # comparing when the elements were added is needed for overlap detection.
                        result = False

            current = current.parent if hasattr(current, "parent") else None

        return self.surface.get_rect(topleft=self.screen_position).collidepoint(_pygame.mouse.get_pos()) and result

    def hide(self) -> _Self:
        if self.mouse_hovering and self.mouse_over_parent():
            _pygame.mouse.set_system_cursor(_pygame.SYSTEM_CURSOR_ARROW)
        self.hidden = True
        return self

    def _register_watch_property(self, name: str):
        attr = getattr(self, name)

        if not isinstance(attr, (int, float)) and not hash(attr):
            raise TypeError(f"Unable to watch property by name ({name}) as it isnt unhashable")
        
        self._watchable_properties.append( (name, attr) )

    def update(self, dt: float, update_elements: bool=True) -> None:
        self.surface.set_alpha(self.surface_transparency*255)
        self.screen_position = self.get_screen_position()
        self.local_mouse_position = self.get_local_mouse_position()
        mouse_over = self.mouse_over_element() and self.mouse_over_parent()

        for i, data in enumerate(self._watchable_properties):
            this_value = getattr(self, data[0])
            if data[1] != this_value:
                self.on_property_changed.fire(data[0], this_value)
                self._watchable_properties[i] = (data[0], this_value)

        if self.sync_mouse:
            if not self.mouse_hovering and mouse_over:
                args = (True, self.local_mouse_position)
                self.on_mouse_hover.fire(*args)

            if self.mouse_hovering and not mouse_over:
                args = (False, self.local_mouse_position)
                self.on_mouse_hover.fire(*args)
            
            self.mouse_hovering = mouse_over

        elif not self.sync_mouse and self.mouse_hovering:
            self.mouse_hovering = False
        
        self.update_components()

        if update_elements:
            for element in self.children:
                element.update(dt)
        
        for tween in self._active_tweens.copy():
            tween.update(dt)
            if tween.finished and tween in self._active_tweens:
                self._active_tweens.remove(tween)

    def set_z(self, z: int) -> _Self:
        self.Z = z
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
            if self.child_off_bounds(element): 
                continue

            if element.hidden: 
                continue

            if element.size[0] <= 0 and element.size[1] <= 0: 
                continue

            element.draw(target_surface)
        
    def handle_event_elements(self, event: _pygame.event.Event) -> None:        
        self.handle_event_components(event)

        for element in self.children:
            if not hasattr(element, "handle_event"): 
                continue

            if self.child_off_bounds(element) and not isinstance(element, SubWindow): 
                continue

            if element.hidden: 
                continue

            if element.size[0] <= 0 and element.size[1] <= 0: 
                continue

            element.handle_event(event)
            if element.mouse_hovering:
                break

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

    def update_surface(self) -> _Self:
        self.surface = _pygame.Surface(self.size, _pygame.SRCALPHA).convert_alpha()
        return self

    def _get_stroke_color(self):
        return (self.stroke_color[0], self.stroke_color[1], self.stroke_color[2], (self.stroke_transparency * 
                                                                                   self.surface_transparency)*255)

    def _get_background_color(self):
        return (self.background_color[0], self.background_color[1], self.background_color[2], self.background_transparency*255)

    def _base_draw(self, target_surface: _pygame.Surface, custom_background_color: tuple[int, int, int] | None=None):
        pos = (self.position[0], self.position[1]-self.get_menu_scroll())

        if self.stroke_thickness > 0 and self.stroke_transparency > 0:
            _pygame.draw.rect(target_surface, self._get_stroke_color(), self.get_stroke_rect(), border_radius=self.get_border_radius(), width=self.stroke_thickness)

        if self.background_transparency > 0:
            _pygame.draw.rect(target_surface, self._get_background_color() if not custom_background_color else (
                custom_background_color[0], custom_background_color[1], custom_background_color[2], self.background_transparency*255), (*pos, *self.size), border_radius=self.get_border_radius(0))

        target_surface.blit(self.surface, pos)

    def draw(self, target_surface: _pygame.Surface) -> None:
        ''' Draws the element to the given surface. This is a placeholder and just draws a blanket element. Use this as a 
        templete for making custom widgets. This is meant to be overriden if you intend on custom drawing.
        '''
        self.surface.fill(COLORS["TRANSPARENT"])
        pos = (self.position[0], self.position[1]-self.get_menu_scroll())

        self.draw_elements(target_surface)
        self._base_draw(target_surface)

        target_surface.blit(self.surface, pos)
    
    def handle_event(self, event: _pygame.event.Event) -> None:
        ''' Handles the element interactivity. This is a placeholder and just handles components until overriden '''
        self.handle_event_elements(event)

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return f"UIElement<{self.parent}, {self.size}, {self.position}, {self.background_color}, {self.stroke_thickness}, {self.stroke_color}, {self.children}, {self.border_radius}, {self.name}>"

    def __eq__(self, value: _Self):
        if isinstance(value, UIElement):
            return self.element_id == value.element_id

        raise TypeError(f"Comparing with type of object {type(value)} is not supported.")
    
    def __ne__(self, value: _Self):
        if isinstance(value, UIElement):
            return self.element_id != value.element_id

        raise TypeError(f"Comparing with type of object {type(value)} is not supported.")

    def __gt__(self, other: _Self):
        raise NotImplementedError("Comparing via greater than is not supported.")

    def __lt__(self, other: _Self):
        raise NotImplementedError("Comparing via less than is not supported.")
    
    def __le__(self, other: _Self):
        raise NotImplementedError("Comparing via less or equal is not supported.")

    def __ge__(self, other: _Self):
        raise NotImplementedError("Comparing via greater or equal is not supported.")

    def __delete__(self, instance: _Self):
        self.destroy()

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
    
    def handle_event(self, event: _pygame.event.Event) -> None:
        '''
            Handles event for the componet. This is meant to be overriden and current does nothing.
        '''


    def init(self) -> None:
        '''
            Initalizes the componet. This is meant to be overriden and currently does nothing.
        '''
    
    def update(self) -> None:
        '''
            This updates the componet. This is meant to be overriden and currently does nothing.
        '''
    
    def __eq__(self, value: "UIComponent"):
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
        self.drag_start = Event()
        self.drag_end = Event()

    def should_start_drag(self, mouse_pos: Coordinate) -> bool:
        '''
            Indicates wehter the component should start dragging. This is meant to be overriden and just returns True
        '''
        return True
    
    def handle_event(self, event: _pygame.event.Event):
        if event.type == _pygame.MOUSEBUTTONDOWN and event.button == 1 and self.element.mouse_hovering and not self.element.hidden:
            if self.should_start_drag(event.pos):
                self.drag_offset = (
                    event.pos[0] - self.element.screen_position[0],
                    event.pos[1] - self.element.screen_position[1]
                )

                self.dragging = True
                self.drag_start.fire()
        
        if event.type == _pygame.MOUSEMOTION and self.dragging:
            mouse_pos = self.element.local_mouse_position
            pos_x = max(self.element.stroke_thickness, mouse_pos[0] - self.drag_offset[0] + self.offset[0])
            pos_y = max(self.element.stroke_thickness, mouse_pos[1] - self.drag_offset[1] + self.offset[1])

            if pos_x + self.element.size[0] + self.element.stroke_thickness >= self.element.parent.size[0]:
                pos_x = self.element.parent.size[0] - self.element.size[0] - self.element.stroke_thickness

            if pos_y + self.element.size[1] + self.element.stroke_thickness > self.element.parent.size[1]:
                pos_y = self.element.parent.size[1] - self.element.size[1] - self.element.stroke_thickness

            self.element.position = (pos_x, pos_y)

        if event.type == _pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            self.dragging = False
            self.drag_end.fire()

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
        return element.clickable if isinstance(element, TextButton) else False

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
        
        if not self.is_icons_clickable() and not self.element.hidden:
            if hasattr(self.element, "_final_color"):
                self.element._final_color = self.element.background_color if not entering else self.element.selected_color
            
            set_cursor_hand(entering)

    def handle_event(self, event: _pygame.event.Event):
        if event.type == _pygame.MOUSEBUTTONUP and event.button == 1 and self.active:
            if self.is_icons_clickable():
                return

            if self.element.mouse_hovering and self.should_click(event.pos):
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

    def handle_event(self, event: _pygame.event.Event):
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
# WIDGET SET
# ----------------------------

class ImageLabel(UIElement):
    '''
        Displayable image as a element.\n
        **NOTE: This is not compatable with border radius.**
    '''
    def __init__(self, parent: UIElement=None, size: Coordinate=(100, 100), position: Coordinate=(0, 0), 
                stroke_thickness: int = 4, stroke_color: tuple[int, int, int]=COLORS["BLACK"], stroke_transparency: float=1, 
                children: list[UIElement]=None, name: str="Image Label", image: _pygame.Surface=None):
        super().__init__(parent, size, position, (0, 0, 0, 0), 0, 0, stroke_thickness, stroke_transparency, stroke_color, children, name)
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

    def handle_event(self, event: _pygame.event.Event):
        self.handle_event_components(event)

    def draw(self, target_surface: _pygame.Surface):
        self.surface.fill(self.background_color)
        self.surface.blit(self._image, (0, 0))
        self.draw_elements(self.surface)
        self._base_draw(target_surface)

class TextButton(UIElement):
    '''
        A clickable button that displays text. This should be used when you want a action to happen when an element is clicked on.
    '''
    def __init__(self, text: str="Hello world!", position: Coordinate=(0,0), action: _Callable=lambda: print("I was clicked!"), size: Coordinate=(100, 35), 
                 background_color: tuple[int, int, int]=None, background_transparency: float=1, selected_color: tuple[int, int, int]=None, stroke_color:  tuple[int, int, int]=COLORS["BLACK"], stroke_thickness: int=4, stroke_transparency: float=1,
                 parent: UIElement=None, clickable: bool=True, children: list[UIElement]=None, border_radius: int=0, name: str="Icon", font: _pygame.font.Font | None=None,
                 text_alignment: tuple[TextXAlignment, TextYAlignment]=(TextXAlignment.middle, TextYAlignment.middle)):
        super().__init__(parent, size, position, background_color, background_transparency, stroke_thickness, stroke_transparency, stroke_color, children=children, name=name, border_radius=border_radius)
        self.on_click = Event()
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

        self.click_component: ClickableComponent = self.add_component(ClickableComponent)[1]
        self.click_component.should_click = lambda _: self.on_click.fire()
        self.click_component.on_click = self.action

        self.text_alignment_x = text_alignment[0]
        self.text_alignment_y = text_alignment[1]
        self.on_mouse_hover.connect(self._on_mouse_hover)
        self.on_click.connect(action)

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

    def handle_event(self, event: _pygame.event.Event) -> None:
        self.handle_event_elements(event)

        if event.type == _pygame.MOUSEBUTTONUP and self.mouse_hovering:
            self._final_color = self.selected_color
    
    def _on_mouse_hover(self, entering, mouse_enter_pos):
        self.click_component.on_mouse_hover(entering, mouse_enter_pos)

        if not entering:
            self._final_color = self.background_color

    def draw(self, target_surface: _pygame.Surface) -> None:
        if self.hidden: return
        if self.size[0] <= 0 or self.size[1] <= 0: return

        if self._final_color != self.background_color and _pygame.mouse.get_pressed()[0]:
            self._final_color = self.background_color

        size = self.surface.get_size()
        self.surface.fill(COLORS["TRANSPARENT"])

        self.surface.blit(self.cached_text_surface, self.get_text_pos())

        self.draw_elements(self.surface)
        self._base_draw(target_surface, self._final_color)

class ImageButton(ImageLabel):
    '''
        A clickable button that displays an image.\n
        **NOTE: This is not compatable with border radius.**
    '''
    def __init__(self, parent: UIElement=None, size: Coordinate=(100, 35), position: Coordinate=(0, 0), 
            stroke_thickness: int = 4, stroke_color: tuple[int, int, int] = COLORS["BLACK"], 
            children: list[UIElement]=None, name: str="Image Label", image: _pygame.Surface=None, clickable: bool=True, action: _Callable=lambda: print("I was clicked!")):
        super().__init__(parent, size, position, stroke_thickness, stroke_color, 1, children, name, image)
        self.hidden = False
        self.clickable = clickable
        self.action = action

        self.click_component = self.add_component(ClickableComponent)[1]
        self.click_component.should_click = lambda _: self.clickable
        self.click_component.on_click = self.action
        self.on_mouse_hover.connect(self._on_mouse_hover)

    def _on_mouse_hover(self, entering, mouse_enter_pos):
        self.click_component.on_mouse_hover(entering, mouse_enter_pos)

class TextBox(UIElement):
    '''
        A text entry for text which supports single line entry and multiline entry.
    '''

    def __init__(self, position=(0, 0), size=(250, 25), parent=None,
                 multi_line: bool = False,
                 children=None, name="TextBox", border_radius=0,
                 background_color=COLORS["DARKER-GRAY"], background_transparency=1,
                 focused_color=COLORS["GRAY"], stroke_color=COLORS["BLACK"], stroke_transparency=1,
                 placeholder_color=COLORS["LIGHTER-GRAY"], placeholder_text="...",
                 clear_text_on_focus=True, font=None,
                 on_selected=None, on_focus_lost: _Callable[[bool, str], None]=None, on_focus: _Callable=None, is_label=False):
        super().__init__(parent, size, position, background_color, background_transparency,
                          stroke_transparency=stroke_transparency, children=children, name=name,
                          stroke_thickness=2, border_radius=border_radius, stroke_color=stroke_color)
 
        self._multi_line = multi_line
        self.is_label = is_label

        self.on_focus = Event()
        self.on_focus_lost = Event()
        self.on_multiline_resize_attempt = Event()
        self.on_mouse_hover.connect(self._on_mouse_hover)

        if on_focus_lost:
            self.on_focus_lost.connect(on_focus_lost)

        if on_focus:
            self.on_focus.connect(on_focus)
        
        self._lines: list[str] = ["Hello world!"]
        self.cursor_line = 0
        self.cursor_colum = 0
 
        self.scroll_x = 0
        self.text_scroll = 0
        self.max_scroll = 300
        self.scrollbar_width = 6
        self.line_gap = 14
 
        self.font = font or _pygame.font.SysFont("consolas", self.surface.get_height()-5 if not multi_line else self.line_gap)
        self.focused = False
        self.editable = True
        self.cursor_visible = True
        self.cursor_enabled = True
        self.now = _time.time()
        self.text_offset_input = 10
 
        self.clear_text_on_focus = clear_text_on_focus
        self.placeholder_color = placeholder_color
        self.placeholder_text = placeholder_text
        self.focused_color = focused_color
        self.text_color: tuple[int, int, int] = COLORS["WHITE"]
 
        self.held_key = False
        self._held_key_tick = _time.time()
        self._held_key_code = ""
        self._now_held_tick = _time.time()
 
        self._line_cache = {}
        self._MAX_CACHE = 4000
 
        self.undo_stack = _Stack([])
        self.undo_stack.on_undo = self._on_undo

        self.on_selected = on_selected
 
        self.selection_anchor = (0, 0)
        self.highlight_color = (166, 210, 255)
        self._mouse_selecting = False
        self.scale_multiline_size = True

    def clear_text(self) -> _Self:
        self.reset_cursor_position()
        self._lines = [""]
        if self._multi_line:
            self.selection_anchor = (0, 0)
            self.held_key = False
            self._line_cache.clear()

        return self

    def set_single_text(self, text: str) -> _Self:
        if self.multi_line:
            return self
        
        self.current_line = ""
        self.current_line = text
        return self

    @property
    def multi_line(self):
        return self._multi_line

    @multi_line.setter
    def multi_line(self, value: bool):
        if not value:
            self.cursor_line = 0

            if len(self._lines) <= 1:
                return
            
            result = ""
            first = self._lines[0]

            for i, line in enumerate(self._lines):
                if i < 0:
                    continue
                result += line

            self._lines.clear()
            self._lines.append(first + result)

        self._multi_line = value

    @property
    def lines(self) -> list[str]:
        return self._lines
 
    @lines.setter
    def lines(self, value):
        if isinstance(value, str):
            self._lines = value.split("\n") if self.multi_line else [value]
        else:
            self._lines = value if value else [""]
 
    @property
    def text(self) -> str:
        return "\n".join(self._lines)
 
    @text.setter
    def text(self, value: str):
        self.lines = value
 
    @property
    def current_line(self) -> str:

        try:
            result = self.lines[self.cursor_line]
        except IndexError:
            result = ""
        
        return result
 
    @current_line.setter
    def current_line(self, value: str):
        self.lines[self.cursor_line] = value

    @property
    def _text_offset(self):
        return (self.border_radius-5 if len(self.text) <= 0 else 0)
 
    def before_cursor(self) -> str:
        return self.current_line[:self.cursor_colum]
 
    def after_cursor(self) -> str:
        return self.current_line[self.cursor_colum:]
 
    def add_char(self, char: str) -> _Self:
        if self.has_selection:
            self.erase_selection()
        
        self._register_undo("char_add")

        self.current_line = self.before_cursor() + char + self.after_cursor()
        self.cursor_colum += 1
        self.cursor_visible = True

        self.now = _time.time()

        if self.multi_line:
            size = (self.size[0], self.size[1] + self.line_gap)
            if self._get_surf_line(self.current_line).get_width() > self.size[0] - self.text_offset_input:
                self.size = size
                self.on_multiline_resize_attempt.fire(True, size)
                self.add_line()
            else:
                self.on_multiline_resize_attempt.fire(False, size)

        self.clear_selection()

        return self
 
    def remove_char(self) -> _Self:
        if self.has_selection:
            self.erase_selection()

            if not self.multi_line:
                self.check_bounds()
            
            return self
        
        if self.cursor_colum > 0:
            self._register_undo("backspace")
            self.current_line = self.current_line[:self.cursor_colum - 1] + self.after_cursor()
            self.cursor_colum -= 1
        elif self.multi_line and self.cursor_line > 0:
            self._register_undo("backspace")
            remainder = self.after_cursor()
            self.lines.pop(self.cursor_line)
            self.cursor_line -= 1
            self.cursor_colum = len(self.current_line)
            self.current_line = self.current_line + remainder

            size = (self.size[0], self.size[1] - self.line_gap)
            if self.cursor_line * self.line_gap < self.size[1] - self.text_offset_input and self.scale_multiline_size:
                self.size = size
                self.on_multiline_resize_attempt.fire(True, size)
            else:
                self.on_multiline_resize_attempt.fire(False, size)

        return self
 
    def add_line(self) -> _Self:
        if not self.multi_line:
            return self

        after, before = self.after_cursor(), self.before_cursor()
        self.current_line = after
        self.lines.insert(self.cursor_line, before)
        self.cursor_line += 1
        self.cursor_colum = 0

        size = (self.size[0], self.size[1] + self.line_gap)
        if self.cursor_line * self.line_gap >= self.size[1] - self.text_offset_input and self.scale_multiline_size:
            self.size = size
            self.on_multiline_resize_attempt.fire(True, size)

        self.clear_selection()
        
        return self
 
    def _register_undo(self, kind: str):
        self.undo_stack.insert({
            "line": self.cursor_line, "col": self.cursor_colum,
            "text": self.current_line, "type": kind,
        })
 
    def _on_undo(self, context, value):
        self.cursor_line = value["line"]
        self.cursor_colum = value["col"]
        self.current_line = value["text"]
 
    def move_left(self):
        if self.cursor_colum > 0:
            self.cursor_colum -= 1
        elif self.multi_line and self.cursor_line > 0:
            self.cursor_line -= 1
            self.cursor_colum = len(self.current_line)
 
    def move_right(self):
        if self.cursor_colum < len(self.current_line):
            self.cursor_colum += 1
        elif self.multi_line and self.cursor_line < len(self.lines) - 1:
            self.cursor_line += 1
            self.cursor_colum = 0
 
    def move_up(self):
        if self.multi_line and self.cursor_line > 0:
            self.cursor_line -= 1
            self.cursor_colum = min(self.cursor_colum, len(self.current_line))
 
    def move_down(self):
        if self.multi_line and self.cursor_line < len(self.lines) - 1:
            self.cursor_line += 1
            self.cursor_colum = min(self.cursor_colum, len(self.current_line))
 
    def handle_return(self):
        if self.multi_line:
            self.add_line()
        else:
            self.focused = False
            self.exit_box(True)

    @property
    def has_selection(self) -> bool:
        return self.selection_anchor is not None and self.selection_anchor != (self.cursor_line, self.cursor_colum)
 
    def get_selection_range(self):
        '''Returns ((start_line, start_col), (end_line, end_col)), normalized so start <= end.'''
        a = self.selection_anchor
        b = (self.cursor_line, self.cursor_colum)
        return (a, b) if a <= b else (b, a)
 
    def get_selected_text(self) -> str:
        if not self.has_selection:
            return ""
        
        (sl, sc), (el, ec) = self.get_selection_range()

        if sl == el:
            return self.lines[sl][sc:ec]
        
        parts = [self.lines[sl][sc:]]

        parts.extend(self.lines[sl + 1:el])
        parts.append(self.lines[el][:ec])

        return "\n".join(parts)
 
    def erase_selection(self) -> _Self:
        if not self.has_selection:
            return self

        self._register_undo("selection_delete")

        (sl, sc), (el, ec) = self.get_selection_range()

        if sl == el:
            self.current_line = self.lines[sl][:sc] + self.lines[sl][ec:]
        else:
            merged = self.lines[sl][:sc] + self.lines[el][ec:]
            new_lines = self.lines[:sl] + [merged] + self.lines[el + 1:]
            self.lines = new_lines
        
        self.cursor_line, self.cursor_colum = sl, sc
        self.clear_selection()

        if self.multi_line:
            size = (self.size[0], len(self.lines) * self.line_gap)
            if self.scale_multiline_size:
                self.on_multiline_resize_attempt.fire(True, size)
                self.size = size
            else:
                self.on_multiline_resize_attempt.fire(False, size)
        else:
            self.check_bounds()

        return self
 
    def clear_selection(self):
        self.selection_anchor = None
 
    def select_all(self):
        self.selection_anchor = (0, 0)
        self.cursor_line = len(self.lines) - 1
        self.cursor_colum = len(self.current_line)
 
    def copy_selection(self):
        if self.has_selection:
            set_clipboard_text(self.get_selected_text())

    def paste_into(self, text: str):
        if self.multi_line:
            for line in text.split("\n"):
                self._register_undo("pasting_multiline")

                for char in line:
                    self.add_char(char)
                
                self.cursor_colum += len(line)
        else:
            self._register_undo("pasting_singleline")
            self.cursor_colum += len(text)
            self.add_char(text)
        
        self.clear_selection()

    def reset_cursor_position(self) -> _Self:
        if not self.multi_line:
            self.cursor_colum = 0
            self.scroll_x = 0
        else:
            self.cursor_colum = 0
            self.cursor_line = 0
            self.text_scroll = 0

        return self

    def handle_event(self, event) -> None:
        self.handle_event_elements(event)
        if self.is_label:
            return
 
        if event.type == _pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.hidden:
            result = (self.mouse_hovering and self.editable) if not callable(self.on_selected) \
                else self.on_selected(self, event, self.local_mouse_position) and self.mouse_hovering
 
            if not result and self.focused:
                self.exit_box(False)
            elif result:
                self.select_text_box()
                if self.clear_text_on_focus:
                    self.text = ""
                    if not self.multi_line:
                        self.scroll_x = 0
                    else:
                        self.text_scroll = 0
 
            self.focused = result
            if self.focused:
                self.now = _time.time()
                self.cursor_visible = True
                self.set_cursor_position(event.pos)
                self.selection_anchor = (self.cursor_line, self.cursor_colum)
                self._mouse_selecting = True
            else:
                self.clear_selection()
 
        if event.type == _pygame.MOUSEBUTTONUP and event.button == 1:
            self._mouse_selecting = False
 
        if event.type == _pygame.MOUSEMOTION and self.focused and self._mouse_selecting and self.editable:
            self.set_cursor_position(event.pos)
            self.cursor_visible = True
            self.now = _time.time()
 
        if event.type == _pygame.KEYDOWN and self.focused and self.editable:
            self.cursor_visible = True
            self.now = _time.time()
            _held_keys = _pygame.key.get_pressed()

            if not self.multi_line:
                self.check_bounds()
 
            if event.key == _pygame.K_BACKSPACE:
                self.remove_char()
                self._start_quick_add(_pygame.K_BACKSPACE)
            elif event.key == _pygame.K_RETURN:
                self.handle_return()
                self._start_quick_add(_pygame.K_RETURN)
            elif event.key == _pygame.K_LEFT:
                self.clear_selection()
                self.move_left()
            elif event.key == _pygame.K_HOME:
                self.reset_cursor_position()
            elif event.key == _pygame.K_ESCAPE:
                self.exit_box(False)
            elif event.key == _pygame.K_RIGHT:
                self.clear_selection()
                self.move_right()
            elif event.key == _pygame.K_UP:
                self.clear_selection()
                self.move_up()
            elif event.key == _pygame.K_DOWN:
                self.clear_selection()
                self.move_down()
            elif event.key == _pygame.K_TAB:
                self.add_char("    ")
                self._start_quick_add(_pygame.K_TAB)
            elif event.key == _pygame.K_a and _held_keys[command_key()]:
                self.select_all()
            elif event.key == _pygame.K_c and _held_keys[command_key()]:
                self.copy_selection()
            elif event.key == _pygame.K_x and _held_keys[command_key()]:
                self.copy_selection()
                self.erase_selection()
            elif event.key == _pygame.K_v and _held_keys[command_key()]:
                if self.has_selection:
                    self.erase_selection()
                
                self.paste_into(get_clipboard_text())
                self._start_quick_add(_pygame.K_v + command_key())
            elif event.key == _pygame.K_z and _pygame.key.get_pressed()[command_key()]:
                self.undo_stack.undo()
                self._start_quick_add(_pygame.K_z + command_key())
            else:
                if len(event.unicode) > 0 and event.unicode.isprintable():
                    self.add_char(event.unicode)
                    self._start_quick_add(event.unicode)
 
        if event.type == _pygame.KEYUP and self.focused and self.editable:
            if event.unicode == self._held_key_code or event.key == self._held_key_code or (command_key() | self._held_key_code if isinstance(self._held_key_code, int) else False):
                self.held_key = False

    def _start_quick_add(self, char):
        self.held_key = True
        self._held_key_code = char
        self._held_key_tick = _time.time()

    def _apply_held_key(self):
        if self.focused and self.held_key and _time.time() - self._held_key_tick > 0.65 and _time.time() - self._now_held_tick > 0.03:
            self._now_held_tick = _time.time()
            if self._held_key_code == _pygame.K_BACKSPACE:
                self.remove_char()
            elif self._held_key_code == _pygame.K_RETURN:
                self.handle_return()
            elif self._held_key_code == _pygame.K_z + command_key():
                self.undo_stack.undo()
            elif self._held_key_code == _pygame.K_v + command_key():
                self.paste_into(get_clipboard_text())
            elif self._held_key_code == _pygame.K_TAB:
                self.add_char("    ")
            else:
                self.add_char(self._held_key_code)

            if not self.multi_line:
                self.check_bounds()
 
    def _on_mouse_hover(self, entering, mouse_enter_pos):
        if self.hidden or not self.editable or self.is_label:
            return
        
        _pygame.mouse.set_cursor(_pygame.SYSTEM_CURSOR_IBEAM if entering else _pygame.SYSTEM_CURSOR_ARROW)

    def select_text_box(self):
        self.on_focus.fire()
        self.focused = True
        return self

    def set_as_label(self, is_label: bool=False) -> _Self:
        '''
            Defines if the textbox will become a text label or not.
        '''
        self.is_label = is_label
        return self

    def exit_box(self, was_enter: bool):
        self.on_focus_lost.fire(was_enter, self.text)
        self.clear_selection()
        self.focused = False

        if self.mouse_hovering:
            _pygame.mouse.set_cursor(_pygame.SYSTEM_CURSOR_ARROW)

        return self
 
    def check_bounds(self):
        if self.font.size(self.text)[0] < self.surface.get_width() - self.text_offset_input:
            self.scroll_x = 0
            return self

        x_pos = self.get_pixel_x()

        if x_pos - self.scroll_x < self.text_offset_input:
            self.scroll_x = max(0, x_pos - self.text_offset_input - self._text_offset)
        elif x_pos > self.surface.get_width() - self.text_offset_input:
            self.scroll_x = x_pos - self.surface.get_width() + self.text_offset_input + self._text_offset

        return self
 
    def get_pixel_x(self):
        return self.font.size(self.before_cursor())[0]
 
    def set_cursor_position(self, position: tuple[float, float]):
        position = self.transform_point_to_local_space(position)
        if self.multi_line:
            local = (position[0] - self.position[0] + self._text_offset, position[1] - self.position[1])
            
            self.cursor_line = min(len(self.lines) - 1, max(0, round(local[1] / self.line_gap) ))

            for x in range(len(self.current_line) + 1):
                if self.font.size(self.current_line[:x])[0] > local[0]:
                    self.cursor_colum = x
                    return self
            
            self.cursor_colum = len(self.current_line)
        else:
            self.cursor_line = 0
            for i in range(len(self.current_line) + 1):
                if self.font.size(self.current_line[:i])[0] > position[0] - self.position[0] + self.scroll_x + self._text_offset:
                    self.cursor_colum = i
                    return self
            self.cursor_colum = len(self.current_line)
        return self

    def _get_surf_line(self, line: str):
        width = max(1, self.font.size(line)[0])
        surf = _pygame.Surface((width, self.line_gap), _pygame.SRCALPHA)
        surf.blit(self.word_formatter(line, self.font, self.font.size(line)), (0, 0))
        return surf
 
    def _render_line(self, line: str):
        cached = self._line_cache.get(line)
        if cached is not None:
            return cached

        surf = self._get_surf_line(line)

        if len(self._line_cache) > self._MAX_CACHE:
            self._line_cache.clear()
        
        self._line_cache[line] = surf

        return surf
 
    def word_formatter(self, word: str, font: _pygame.font.Font, word_size: tuple[int, int]):
        '''
            Used for custom rendering of a word in textbox. 
        '''
        return font.render(word, True, self.text_color)

    def update(self, dt: float, update_elements: bool=True):

        if not self.editable:
            self.cursor_visible = False
        
        return super().update(dt, update_elements)

    def _draw_single_line(self):
        if self.has_selection and not self.is_label:
            _, sc, _, ec = self.get_selection_range()
            x0 = self.font.size(self.text[:sc])[0] - self.scroll_x + self._text_offset
            x1 = self.font.size(self.text[:ec])[0] - self.scroll_x + self._text_offset

            _pygame.draw.rect(self.surface, self.highlight_color,
                               (x0 + self._text_offset, 1, x1 - x0, self.surface.get_height()))

        text_surface = self.font.render(self.text if self.text else self.placeholder_text, True, 
                                        self.text_color if len(self.text) > 0 else self.placeholder_color)
        
        self.surface.blit(text_surface, (-self.scroll_x + self._text_offset, self.surface.get_height() / 2 - text_surface.get_height() / 2))

        if self.focused and self.cursor_visible and self.editable and not self.is_label:
            x_pos = self.get_pixel_x()
            _pygame.draw.line(self.surface, COLORS["WHITE"],
                               (x_pos - self.scroll_x + self._text_offset, 2),
                               (x_pos - self.scroll_x + self._text_offset, 
                                self.surface.get_height() - self.surface.get_height() / 8), 2)

    def _draw_multi_line(self):
        self.max_scroll = self.surface.get_height() - 1
        first = max(0, int(self.text_scroll // self.line_gap))
        count = int(self.surface.get_height() // self.line_gap) + 2
        last = min(len(self.lines), first + count)
 
        if self.has_selection and not self.is_label:
            (selection_line, selection_colum), (end_line, end_colum) = self.get_selection_range()

            for i in range(max(first, selection_line), min(last, end_line + 1)):
                line = self.lines[i]

                start_col = selection_colum if i == selection_line else 0
                end_col = end_colum if i == end_line else len(line)

                x0 = self.font.size(line[:start_col])[0]
                x1 = self.font.size(line[:end_col])[0] if line else x0 + 6
                y = i * self.line_gap - self.text_scroll

                _pygame.draw.rect(self.surface, self.highlight_color,
                                   (x0, y, max(2, x1 - x0), self.line_gap))
 
        for i in range(first, last):
            line_y = i * self.line_gap - self.text_scroll

            self.surface.blit(self._render_line(self.lines[i]), (0, line_y))
 
        if self.cursor_visible and self.cursor_enabled and self.focused and self.editable and not self.is_label:
            cursor_x = self.font.size(self.current_line[:self.cursor_colum])[0]
            cursor_y = (self.cursor_line * self.line_gap) - self.text_scroll

            _pygame.draw.line(self.surface, self.text_color, (cursor_x, cursor_y), 
                              (cursor_x, cursor_y + self.line_gap))

    def draw(self, target_surface=None) -> None:
        if self.hidden:
            if self.focused:
                self.exit_box(False)
            return

        if self.is_label and self.focused:
            self.exit_box(False)

        if not self.is_label and self.mouse_hovering:
            _pygame.mouse.set_cursor(_pygame.SYSTEM_CURSOR_IBEAM)
        
        if self.size[0] <= 0 or self.size[1] <= 0:
            return
        
        self.surface.fill(COLORS["TRANSPARENT"])
        self._apply_held_key()
 
        if self.multi_line:
            self._draw_multi_line()
        else:
            self._draw_single_line()

        if not self.is_label:
            if self.focused and _time.time() - self.now > 0.5 and self.editable:
                self.now = _time.time()
                self.cursor_visible = not self.cursor_visible
            elif not self.focused:
                self.cursor_visible = True
 
        self.draw_elements(self.surface)
        self._base_draw(target_surface, self.focused_color if self.focused else self.background_color)

class Bar(UIElement):
    '''
        A resizable bar element. This should be used ethier as a slider or as a progress bar.
    '''
    def __init__(self, parent: UIElement=None, size: Coordinate=(150, 25), position: Coordinate=(0, 0), 
                 background_color: tuple[int, int, int]=None, background_transparency: float=1, foreground_color: tuple[int, int, int]=COLORS["WHITE"], stroke_thickness: int=4, stroke_transparency: float=1,
                 stroke_color=COLORS["BLACK"], children: list[UIElement]=None, name: str="Bar", border_radius: int=0, resizeable: bool=True):
        super().__init__(parent, size, position, background_color, background_transparency, stroke_thickness, stroke_transparency, stroke_color, children=children, name=name, border_radius=border_radius)
        self.bar_percent = 0.5
        self.resize_click_range = 30
        self.foreground_color = foreground_color
        self.resizeable = resizeable
        self.resizing = False
        self._register_watch_property("bar_percent")

    def set_percent(self, new_percent: float) -> _Self:
        '''
            Sets the bar percent.
        '''
        self.bar_percent = new_percent
        return self

    def handle_event(self, event: _pygame.event.Event) -> None:
        self.handle_event_elements(event)

        if event.type == _pygame.MOUSEBUTTONDOWN and event.button == 1 and self.mouse_over_parent() and self.resizeable:
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
        self.surface.fill(COLORS["TRANSPARENT"])

        _pygame.draw.rect(self.surface, self.foreground_color, (0, 0, self.size[0]*self.bar_percent, self.size[1]), border_radius=self.get_border_radius())

        self.draw_elements(self.surface)
        self._base_draw(target_surface)

class Menu(UIElement): 
    '''
        A scrollable menu element. This should be used to contain other elements and be scrollable.
    '''
    def __init__(self, position: Coordinate=(0, 0), size: Coordinate=(350, 200), children: list[UIElement]=None, 
                 stroke_thickness: int=3, stroke_transparency: float=1, stroke_color: tuple[int, int, int] | None=None, background_color: tuple[int, int, int]=None, background_transparency: float=1,
                 parent: UIElement=None, name: str="ScrollableMenu", max_scroll: int=0, border_radius: int=0, scroll_speed: int=10):
        super().__init__(parent, size, position, background_color or COLORS["DARKER-GRAY"], background_transparency, stroke_thickness, stroke_transparency, stroke_color, children, border_radius, name)
        self.scroll_y = 0
        self.scrollable = True
        self.max_scroll = max_scroll
        self.layout = None
        self.focused = False
        self.current_scrollbar_rect = None
        self.scrollbar_dragging = False
        self.scrollbar_offset = 0
        self.scroll_speed = scroll_speed
        self.scroll_velocity = 0
        self._scroll_decrement = self.scroll_speed/20
        self._stop_handling_children_events = False
        self.scrollbar_width = 6
        self._register_watch_property("scroll_y")
    
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
        self.max_scroll = max(0, content_bottom - self.size[1]) + offset + 50

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

    def handle_event(self, event: _pygame.event.Event) -> None:
        if not self._stop_handling_children_events:
            self.handle_event_elements(event)

        if event.type == _pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.hidden and self.mouse_over_parent():
            local_p = self.local_mouse_position if self.parent else event.pos

            if not hasattr(self, "on_selected"):
                result = self.mouse_hovering
            else:
                result = self.on_selected(self, event, local_p)
            
            self.focused = result

            if self.focused and self.scrollable and self.max_scroll > 0:
                pos = self.local_mouse_position
                self.scrollbar_dragging = self.current_scrollbar_rect.collidepoint(pos)
                self.scrollbar_offset = pos[1]-self.current_scrollbar_rect.y

        elif event.type == _pygame.MOUSEWHEEL and self.focused and self.scrollable and self.mouse_hovering:
            for v in self.children:
                if isinstance(v, Menu) and v.focused and v.parent is self:
                    return

            self.scroll_velocity = event.y*-self.scroll_speed

        elif event.type == _pygame.MOUSEBUTTONUP and self.scrollbar_dragging:
            self.scrollbar_dragging = False

        elif event.type == _pygame.MOUSEMOTION and self.scrollbar_dragging:
            self.scroll_velocity = 0
            percent = max(0, min(1, (self.local_mouse_position[1]-self.position[1]-self.scrollbar_offset-
            (self.title_bar_height if isinstance(self, SubWindow) else 0)) / 
                (self.surface.get_height() - self.current_scrollbar_rect.height) 
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
        
        if self.layout is not None and len(self.children) > 0:
            self.layout.update()

        self.surface.fill(COLORS["TRANSPARENT"])

        self.draw_elements(self.surface)
        
        if self.scrollable and self.max_scroll > 0:
            scrollbar_rect = self._get_scrollbar_rect(self.scroll_y, self.max_scroll, self.scrollbar_width)
            _pygame.draw.rect(self.surface, COLORS["WHITE"], scrollbar_rect, border_radius=15)
            self.current_scrollbar_rect = _pygame.Rect(*scrollbar_rect)

        self._base_draw(target_surface)

class CheckBox(TextButton):
    '''
        A check button which holds a True or False value. This should be used for toggleable values from the user.
    '''
    def __init__(self, text: str="Enabled", position: Coordinate=(0, 0), parent: UIElement=None, checked: bool=False, 
                 on_flip: _Callable=lambda enabled: print(enabled), size: Coordinate=(160, 30), border_radius: int=0, background_transparency: float=1, stroke_transparency: float=1):
        def flip() -> None: 
            self._checked = not self._checked
            self.on_flip.fire(self.get_value())

        super().__init__(text, position, size=size, parent=parent, clickable=True, action=flip, background_color=COLORS["LIGHTER-GRAY"], border_radius=border_radius, stroke_transparency=stroke_transparency, background_transparency=background_transparency)

        self.on_flip = Event()

        if on_flip:
            self.on_flip.connect(on_flip)
        
        self._checked = checked
        self.stroke_thickness = 2
        height = self.size[1]-15
        self.check_box_rect = _pygame.Rect(5, self.size[1]/2-height/2, self.size[0]*0.10, height)
        self.click_component.should_click = lambda mouse_pos: self.get_checkbox_rect().collidepoint(mouse_pos)
        self._register_watch_property("_checked")

    def get_value(self) -> bool:
        return self._checked

    def get_checkbox_rect(self) -> _pygame.Rect:
        return _pygame.Rect(
            self.check_box_rect.x + self.screen_position[0],
            self.check_box_rect.y + self.screen_position[1],
            *self.check_box_rect.size
        )

    def draw(self, target_surface: _pygame.Surface) -> None:
        self.surface.fill(COLORS["TRANSPARENT"])

        _pygame.draw.rect(self.surface, COLORS["GREEN"] if self._checked else COLORS["RED"], self.check_box_rect)
        self.surface.blit(self.cached_text_surface, (self.size[0]*0.18, self.size[1]/2-self.cached_text_surface.get_height()/2))

        self.draw_elements(self.surface)
        self._base_draw(target_surface)

class SubWindow(Menu):
    '''
        A draggable menu. This should be used to hold other elements the user can move around willingly.\n
        **NOTE: Scrollbar visual may clip out of the window slightly.**
    '''
    def __init__(self, position: Coordinate=(0, 0), size: Coordinate=(350, 200), children: list[UIElement]=None, 
                stroke_thickness: int=3, background_color: tuple[int, int, int]=None, parent: UIElement=None, name: str="SubWindow", 
                max_scroll: int=0, title: str="Sub Window!", title_bar_height: int=25, border_radius: int=0, title_text_color: tuple[int, int, int]=COLORS["WHITE"],
                title_bar_color: tuple[int, int, int]=COLORS["LIGHTER-GRAY"], title_bar_font: _pygame.font.Font | None=None, background_transparency: float=1, stroke_transparency: float=1, stroke_color: tuple[int, int, int] | None=None):
        super().__init__(position, size, children, stroke_thickness, stroke_transparency, stroke_color, background_color, background_transparency, parent, name, max_scroll, border_radius=border_radius)
        self.title_bar_height = title_bar_height
        self.sub_surface = _pygame.Surface((self.size[0], self.size[1]-self.title_bar_height), _pygame.SRCALPHA)
        self.titlebar_surface = _pygame.Surface((self.size[0], self.title_bar_height), _pygame.SRCALPHA)
        self.title_bar_text_font = title_bar_font or _global_font

        self._title = title
        self._cached_text_surface = self.title_bar_text_font.render(self.title, True, (255, 255, 255))
        self.title_bar_color = title_bar_color

        self._title_text_color = title_text_color

        self.drag_component: DragComponent = self.add_component(DragComponent)[1]

        self.drag_component.should_start_drag = lambda pos: self.titlebar_surface.get_rect(topleft=self.screen_position).collidepoint(pos)
        self._border_radius = self.border_radius

        self._close_button = self.title_bar_text_font.render("X", True, COLORS["WHITE"])
        self._close_button_position = (self.size[0] - self._close_button.get_width()-20, 5)

        self._minimize_button = self.title_bar_text_font.render("-", True, COLORS["WHITE"])
        self._minimize_button_position = (self.size[0] - self._close_button.get_width()-50, 5)

        self._minimized = False

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
    def minimized(self):
        return self._minimized
    
    @minimized.setter
    def minimized(self, value: bool):
        self._minimized = value

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

    def _buttons(self):
        final_position = (
            self.screen_position[0] + self._close_button_position[0],
            self.screen_position[1] + self._close_button_position[1]
        )

        if self._close_button.get_rect(topleft=final_position).collidepoint(_pygame.mouse.get_pos()):
            self.destroy()

    def handle_event(self, event: _pygame.event.Event):
        super().handle_event(event)

        if event.type == _pygame.MOUSEBUTTONDOWN and self.focused:
            self._buttons()

    def update(self, dt: float):
        return super().update(dt, not self.minimized)

    def draw(self, target_surface: _pygame.Surface=None) -> None:
        if self.hidden: return
        if self.size[0] <= 0 or self.size[1] <= 0: return
        self._minimize_button_position = (self.size[0] - self._close_button.get_width()-50, 5)
        self._close_button_position = (self.size[0] - self._close_button.get_width()-20, 5)
        
        if self.layout is not None and len(self.children) > 0:
            self.layout.update()

        self.surface.fill(COLORS["TRANSPARENT"])
        self.sub_surface.fill(COLORS["TRANSPARENT"])
        self.titlebar_surface.fill(COLORS["TRANSPARENT"])

        self.children.sort(key=lambda a: a.Z)

        if not self.minimized:
            self.draw_elements(self.sub_surface)        

        self.titlebar_surface.blit(self._cached_text_surface, (5, self.title_bar_height/2-self._cached_text_surface.get_height()/2))

        if self.scrollable and self.max_scroll > 0:
            scrollbar_rect = self._get_scrollbar_rect(self.scroll_y, self.max_scroll, self.scrollbar_width)

            self.current_scrollbar_rect = _pygame.Rect(*scrollbar_rect)

            _pygame.draw.rect(self.sub_surface, COLORS["LIGHTER-GRAY"], scrollbar_rect)

        _pygame.draw.rect(self.surface, self.title_bar_color, 
                        ((0, 0), (self.size[0], self.titlebar_surface.get_height())), border_top_left_radius=self.get_border_radius(), 
                        border_top_right_radius=self.get_border_radius())

        self.surface.blit(self.titlebar_surface, (0, 0))

        if not self.minimized:
            self.surface.blit(self.sub_surface, (0, self.title_bar_height))

        self.surface.blit(self._close_button, self._close_button_position)
        #self.surface.blit(self._minimize_button, self._minimize_button_position)

        _pygame.draw.line(self.surface, self.stroke_color, (0 if not self.minimized else -self.stroke_thickness, self.title_bar_height), (self.size[0] if not self.minimized else self.size[0]+self.stroke_thickness, self.title_bar_height), 3)

        self._base_draw(target_surface)

class VideoElement(UIElement):
    '''
        A element that playbacks loaded VideoData.
    '''
    def __init__(self, parent: UIElement=None, size: Coordinate=(400, 250), position: Coordinate=(0, 0), 
                 background_color: tuple[int, int, int]=None, foreground_color: tuple[int, int, int]=COLORS["WHITE"], stroke_thickness: int=4, 
                 stroke_color=COLORS["BLACK"], children: list[UIElement]=None, name: str="VideoElement", border_radius: int=0, 
                 video_data: VideoElementData | None=None, background_transparency: float=1, stroke_transparency: float=1):
        super().__init__(parent, size, position, background_color, background_transparency, stroke_thickness, stroke_transparency, stroke_color, children, border_radius, name)
        self.video_data = video_data or VideoElementData([], 60)
        
        self.current_frame = 0
        self._timer = 0
        self._scale_frames = True
        self.paused = False

    def play(self) -> _Self:
        '''
            Plays the given video element. Does this by unpausing it regardless of if already playing.
        '''
        self.paused = False
        return self

    def pause(self) -> _Self:
        '''
            Pauses the given video element. Does this by pausing it regardless of if already paused.
        '''
        self.paused = True
        return self

    def set_frame_rate(self, frame_rate: int) -> _Self:
        '''
            Sets the given video data's frame rate to the new frame rate.
        '''
        self.video_data.frame_rate = frame_rate
        return self

    def update(self, dt: float, _=True):
        super().update(dt, True)

        if self.paused:
            return

        self._timer += dt

        if self._timer > 1/self.video_data.frame_rate:
            self._timer = 0
            self.current_frame += 1
            if self.current_frame > len(self.video_data.frames)-1:
                self.current_frame = 0

    def draw(self, target_surface: _pygame.Surface):
        self.surface.fill(COLORS["TRANSPARENT"])

        if self.video_data.frames:
            frame = self.video_data.get_video_frame(self.current_frame)
            self.surface.blit(frame if not self._scale_frames else _pygame.transform.scale(frame, self.size), (0, 0))

        self.draw_elements(self.surface)
        self._base_draw(target_surface)

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
            for element in element.children:
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

print(f"SparseGUI v1.3.3 (pygame {_pygame.ver}, Python {_sys.version[0:6]})")

# Defining what is imported if import * is used on this module
__all__: list[str] = [name for name, obj in globals().items() if not (name[0] == "_" or name.startswith("_"))]
