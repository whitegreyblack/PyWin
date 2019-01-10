"""window.py"""

import curses
from source.utils import Event


class Window:
    window_ids = 0
    def __init__(self, window, title=None, focused=False, showing=True, border=False):
        self.title = title
        y, x = window.getmaxyx()
        self.term_width = x
        self.term_height = y
        self.window = window
        self.showing = True
        self.parent = None
        self.child = False
        self.border = border
        self.width = x - 2
        self.height = y - 2
        self.components = []
        self.windows = []
        self.views = []
        self.index = 0
        self.focused = focused

        # Window.window_ids[2**w] = self
        self.wid = 2**Window.window_ids
        Window.window_ids += 1

    def add_component(self, component):
        self.components.append(component)

    @property
    def windows(self):
        for window in self.__windows:
            # if hasattr(window, 'selected') and window.selected:
            yield window

    @windows.setter
    def windows(self, value):
        self.__windows = value

    def add_view(self, view):
        self.views.append(view)

    def add_window(self, window):
        window.parent = self
        window.border = True
        self.__windows.append(window)

    def add_windows(self, windows):
        for w in windows:
            self.add_window(w)

    def add_keymap(self, keymap):
        self.keymap = keymap

    def change_window(self):
        self.window.selected = False

    def get_window(self, window_id):
        for window in self.windows:
            if window.wid == window_id:
                return window

    def draw(self):
        """
        Handles erasing of window, border drawing and title placement.
        Then calls children object draw functions
        """
        self.erase()
        self.draw_border()

        if self.title:
            x, y, s = 0, 2, self.title[:self.term_width//2]
            # children titles are -1 from the right
            if self.parent:
                y = self.term_width-len(s)-1
            self.window.addstr(x, y, s)

        if not self.parent:
            dimensions = f"{self.term_width}, {self.term_height}"
            self.window.addstr(
                self.term_height - 1, 
                self.term_width - len(dimensions) - 1, 
                dimensions
            )

        for window in self.windows:
            if window.showing:
                window.draw()
        # for view in self.views:
        #     # view.window.border()
        #     view.draw()

        # for comp in self.components:
        #     comp.draw()

    def erase(self):
        self.window.erase()

    def clear(self):
        for view in self.views:
            view.clear()

    def draw_border(self):
        if self.border:
            self.window.border()

# more specific classes
class DisplayWindow(Window):
    def __init__(self, window, title=None, focused=False):
        super().__init__(window, title, focused)
        self.dataobject = None
        self.selected = -1

    def on_data_changed(self, sender, sid, arg):
        self.dataobject = arg
    
    def draw(self):
        super().draw()
        if self.dataobject:
            mx, my = self.width, self.height
            for y, x, s in self.dataobject.display(1, 1, mx, my, 2):
                if len(s) >= mx:
                    raise BaseException(s)
                self.window.addstr(y, x, s)
        else:
            self.window.addstr(2, 2, "No data present")

    def handle_key(self, key):
        if key == curses.KEY_DOWN:
            pass

class PromptWindow(Window):
    def __init__(self, window, title=None, focused=False, showing=False):
        super().__init__(window, title, focused, showing)
        self.showing = showing

    def draw(self):
        super().draw()
        y, x = self.window.getbegyx()
        curses.curs_set(2)
        self.window.addch(1, 1, ' ')
        self.window.refresh()
    
    def erase(self):
        super().erase()
        curses.curs_set(0)

class ScrollableWindow(Window):
    def __init__(
            self, 
            window, 
            title=None, 
            data=None, 
            focused=False,
            border=True,
            data_changed_handlers=None):
        super().__init__(window, title, focused, border=border)
        self.data_changed_event = Event()
        self.keypress_up_event = Event()
        self.keypress_down_event = Event()

        if data_changed_handlers:
            for handler in data_changed_handlers:
                self.data_changed_event.append(handler)

        self.data = data
        self.selected = -1
        self.index = 0 if self.data else -1

    @property
    def data(self):
        return self.__data
    
    @data.setter
    def data(self, data):
        self.__data = data
        self.on_data_changed()
    
    def on_data_changed(self):
        if self.__data and self.index > -1:
            self.data_changed_event(
                self.__class__.__name__, 
                self.wid, 
                self.index
            )

    def draw(self):
        if not self.showing:
            return

        super().draw()
        rows_in_view = None
        s, e = 0, self.height
        halfscreen = self.height // 2

        if len(self.data) > self.height:
            if self.index < halfscreen:
                pass
            elif self.index > len(self.data) - halfscreen - 1:
                s = len(self.data) - self.height
                e = s + self.height + 1
            else:
                s = self.index - halfscreen
                e = s + self.height
            rows_in_view = self.data[s:e]
        else:
            s = 0
            rows_in_view = self.data

        for i, r in enumerate(rows_in_view):
            l = r[:self.width].ljust(self.width)
            c = curses.color_pair((s + i == self.index) * 2)
            self.window.addstr(i + 1, 1, l, c)

    def handle_key(self, key):
        if key == curses.KEY_DOWN:
            self.keypress_down_event(self)
        elif key == curses.KEY_UP:
            self.keypress_up_event(self)

    # def increment_index(self):
    #     t = self.index + 1
    #     if t < len(self.data):
    #         self.index = t
    #         self.on_data_changed()
    
    # def decrement_index(self):
    #     t = self.index - 1
    #     if t >= 0:
    #         self.index = t
    #         self.on_data_changed()

def on_keypress_down(obj):
    t = obj.index + 1
    if t < len(obj.data):
        obj.index = t
        obj.on_data_changed()

def on_keypress_up(obj):
    t = obj.index - 1
    if t >= 0:
        obj.index = t
        obj.on_data_changed()

# def increment_index(scrollobj):
#     t = scrollobj.index + 1
#     if t < len(scrollobj.data):
#         scrollobj.index = t
#         scrollobj.self.on_data_changed()

# def decrement_index(self):
#     t = self.index - 1
#     if t >= 0:
#         self.index = t
#         self.on_data_changed()