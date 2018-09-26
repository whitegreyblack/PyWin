#!/usr/bin/env python3
"""controls.py:
User Interface Control Components
"""

"""
Parent (UIControl)?
Bounding boxes?

Window: vs Panel:?
    + Panel vs Window?
        - ScrollList
        - Prompt
        - Form
    Move to json?
"""

__author__ = "Samuel Whang"

import curses
from collections import namedtuple
from source.utils import border
from source.utils import format_float as Money

line = namedtuple("Line", "x y line")
def intersect(this, other):
    return False

class UIControl:
    def __init__(self, x, y, width, height, title=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.title = title
        
        self.children = []
        self.isSelected = False
        self.isFocused = False

    def check_bounds(self):
        for child in self.children:
            for other in self.children:
                if child != other and intersect(child, other):
                    raise ValueError(f"{child} and {other} intersect")

    def selected(self):
        """Returns all values within the view that are selected (1...n)"""
        pass

    def focused(self):
        """Returns a single value within the view that is currently focused"""
        pass

class View(UIControl):
    """Implements view screen and control over a single view within a window"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.windows = []

class Window:
    def __init__(self, title, x, y):
        self.title = title
        self.term_width = x
        self.term_height = y
        self.width = x - 2
        self.height = y - 2
        self.windows = []
        self.index = 0

    @property
    def window(self):
        for window in self.windows:
            if hasattr(window, 'selected') and window.selected:
                return window

    def add_window(self, window):
        self.windows.append(window)

    def add_windows(self, windows):
        for window in windows:
            self.windows.append(window)

    def add_keymap(self, keymap):
        self.keymap = keymap

    def change_window(self):
        self.window.selected = False

    def get_window(self, window_id):
        for window in self.windows:
            if window.wid == window_id:
                return window

    def send_signal(self, command, debug=False):
        if (command, self.window.wid) in self.keymap:
            retval = self.window.get_signal(command)
            
            if retval is False:
                return retval

            if self.window.wid == 'ScrollList':
                self.get_window('Form').model = self.window.model

            next_window_id = self.keymap[(command, self.window.wid)]

            if next_window_id is None:
                return False
           
            if next_window_id is not self.window.wid:
                next_window = self.get_window(next_window_id)
                self.window.selected = False
                next_window.selected = True
                if next_window.wid == 'Prompt':
                    next_window.visible = True
        return True

    def draw(self, screen):
        screen.border()
        # screen.addstr(0, 1, self.title)
        dimensions = f"{self.term_width}, {self.term_height}"
        # screen.addstr(0, self.term_width - len(dimensions) - 1, dimensions)
        for window in self.windows:
            window.draw(screen)

# TODO Create a button class to pass into Prompt confirm/cancel parameters
class Button(UIControl):
    def __init__(self, x, y, width, height, label, selected=False):
        super().__init__(x, y, width, height, None)
        self.label = label
        self.selected = selected

    def select(self):
        self.selected = True

    def unselect(self):
        self.selected = False

    def draw(self, screen):
        border(screen, self.x, self.y, self.width, self.height)
        # boxstring = f"x:{self.x}, y:{self.y}, w:{self.width}, h:{self.height}"
        # screen.addstr(self.height + 1, 0, boxstring) 
        if self.selected:
            color = curses.color_pair(2)
        else:
            color = curses.color_pair(1)
        screen.addstr(self.height + self.y - 1, 
                      self.x + self.width - len(self.label) - 1,
                      self.label, color)
 
class Prompt(UIControl):
    def __init__(
            self, 
            window, 
            title=None, 
            confirm=None, 
            cancel=None, 
            wid='Prompt', 
            logger=None
        ):
        self.window = window
        oy, ox = window.getbegyx() # offset from parent window
        my, mx = window.getmaxyx()

        super().__init__(0, 0, mx, my, title)
        self.wid = wid
        self.selected = False
        self.visible = False
        self.logger = logger
        longerlabel = max(len(confirm), len(cancel))
        self.confirm = Button(self.x + 1, 
                              self.height - 4, 
                              longerlabel + 2, 
                              2, 
                              confirm, 
                              True)

        self.cancel = Button(self.width - 3 - longerlabel - 1, 
                             self.height - 4, 
                             longerlabel + 2, 
                             2, 
                             cancel)

        # TODO should be changeable through constructor
        # class button: property isSelected/Selected

    @property
    def button(self):
        # TODO: a better way to access buttons. What if we have multiple? Or a single one?
        for button in [self.confirm, self.cancel]:
            if button.selected:
                return button

    def get_signal(self, command, debug=False):
        # unselect first then select in all cases
        if command == 10 or command == curses.KEY_ENTER:
            self.logger.info("GOT ENTER")
            if self.button is self.cancel:
                self.cancel.unselect()
                self.confirm.select()
                self.visible = False

            elif self.button is self.confirm:
                return False

        if command == ord('y'):
            return False
        
        if command == ord('n'):
            self.visible = False

        if command == curses.KEY_LEFT:
            if self.button is self.cancel:
                self.cancel.unselect()
                self.confirm.select()

        if command == curses.KEY_RIGHT:
            if self.button is self.confirm:
                self.confirm.unselect()
                self.cancel.select()

        if command == ord('\t'):
            if self.button is self.cancel:
                self.cancel.unselect()
                self.confirm.select()
            else:
                self.confirm.unselect()
                self.cancel.select()
        return True

    def draw(self, screen):
        if self.visible:
            dx = self.width - self.x
            dy = self.height - self.y
            # screen.erase()
            self.window.erase()
            # self.window.bkgdset(' ', curses.color_pair(2))
            self.window.border()
            boxstring = f"x:{self.x}, y:{self.y}, w:{self.width}, h:{self.height}"
            # self.window.addstr(0, self.width - len(boxstring) - 1, boxstring)
            self.window.addstr(2, 2, "Are you sure you want to quit?");
            self.confirm.draw(self.window)
            self.cancel.draw(self.window)

class ScrollList:
    """ScrollList should be able to take in any model type that is wrapped in
    a Card class. As long as the items come in as Cards scrolllsit should be
    able to scroll through a list longer than the height of the screen,
    highlight items, and select with highlighting.
    Should implement select, focus, scroll. If selected, card item becomes
    focused. Should still be able to scroll through other items however.

    TODO: inherit from UIControl. Make it also loggable?
    """
    def __init__(self, x, y, width, height, title=None, wid='ScrollList', selected=False):
        self.wid = wid
        self.items = []
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.title = title
        self.index = 0
        self.selected = selected

    def add_item(self, item):
        self.items.append(item)

    def add_items(self, items):
        for item in items:
            self.items.append(item)

    def item_is_selected(self):
        if not self.items:
            return None
        return self.items[self.index].selected

    # def item_is_focused(self):
    #     if not self.items:
    #         return None
    #     return self.items[self.index].focused

    @property
    def model(self):
        if self.items:
            return self.items[self.index]
        return None

    def get_signal(self, command, debug=False):
        if command == curses.KEY_DOWN:
            self.index = min(self.index + 1, len(self.items) - 1)
        elif command == curses.KEY_UP:
            self.index = max(self.index - 1, 0)

    def draw(self, screen):
        dx = self.width - self.x
        dy = self.height - self.y
        border(screen, self.x, self.y, dx, dy)
        
        if self.title:
            screen.addstr(self.y, self.x + 1, self.title) 

        screen.addstr(self.y, self.x - 1, str(self.index))
        # if self.item_is_focused() and self.item_is_selected():
        #     screen.addstr(self.y + 1, self.x - 1, "FS")
        if self.item_is_selected():
            screen.addstr(self.y + 1, self.x - 1, "S")
        for index, item in enumerate(self.items):
            item.draw(screen,
                      self.x + 1, 
                      self.y + index + 1, 
                      self.width,
                      self.height,
                      self.selected,
                      self.index == index)

            # if self.index == index:
            #     for x in (self.x, self.width):
            #         y = self.y + index + 1
            #         c = curses.color_pair(1)
            #         if self.item_is_selected() and self.item_is_focused():
            #             c = curses.color_pair(2)
            #         elif self.item_is_selected():
            #             c = curses.color_pair(3)
            #         screen.addch(y, x, curses.ACS_BLOCK, c)
        
class Card:
    def __init__(self, model, title=None):
        self.model = model
        self.title = title
        self.selected = False

    def format_description(self, length):
        fields = self.model.description
        formats = self.model.formats
        space = max(0, length - sum(len(fo.format(fi)) 
                        for fi, fo in zip(fields, formats)))

        # minimum width should be 80? 
        if space == 0:
            fields = self.model.short_description
            space = max(0, length - sum(len(fo.format(fi))
                        for fi, fo in zip(fields, formats)))

        return self.model.format_criteria.format(fields[0],
                                                 ' ' * space,
                                                 fields[1])

    def draw(self, screen, x, y, dx, dy, focused, selected):
        description = self.format_description(dx - x)
        color = curses.color_pair(1)
        if focused and selected:
            color = curses.color_pair(3)
        elif selected:
            color = curses.color_pair(2)
        screen.addstr(y, x, description, color)

class Form:
    def __init__(self, x, y, width, height, model=None, wid='Form', title=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.model = model
        self.wid = 'Form'
        self.title = title
        self.selected = False

class RecieptForm(Form):
    #def __init__(self, x, y, width, height, model, title=None):
    #    super().__init__(wid, x, y, width, height, model, title)

    def draw(self, screen):
        def pad(word):
            return '.' * max(0, 34 - len(word))

        self.lines = []
        
        border(screen, self.x, self.y, self.width, self.height - self.y)
        # screen.addstr(self.y, 
        #         self.width + self.x - len(f"x:{self.x}, y:{self.y}, w:{self.width}, z:{self.height}"), 
        #         f"x:{self.x}, y:{self.y}, w:{self.width}, z:{self.height}")

        if self.model:
            vertical_offset = 1
            title = self.title if self.title else "Reciept"
            self.lines.append(line(self.x + 1, self.y + vertical_offset, title))
            vertical_offset += 2
            
            for prop in ["store", "date", "category"]:
                label = prop.capitalize()
                value = getattr(self.model.model, prop)
                message = f"{label}{pad(prop)}: {value:>20}"
                l = line(self.x + 1, self.y + vertical_offset, message)
                self.lines.append(l)
                vertical_offset += 1
            vertical_offset += 1

            l = line(self.x + 1, self.y + vertical_offset, "Products:")
            self.lines.append(l)
            vertical_offset += 1

            for product in self.model.model.products:
                message = f"-{product.name:.<33}: {Money(product.price):>20}"
                l = line(self.x + 1, self.y + vertical_offset, message)
                self.lines.append(l)
                vertical_offset += 1
            vertical_offset += 1

            for prop in self.model.model.transaction.properties:
                label = prop.capitalize()
                value = getattr(self.model.model.transaction, prop)
                message = f"{label}{pad(prop)}: {Money(value):>20}"
                # screen.addstr(self.y + product_index,
                #               self.x + 1,
                #               f"{prop}{pad(prop)}: {Money(value):>20}")
                l = line(self.x + 1, self.y + vertical_offset, message)
                self.lines.append(l)
                vertical_offset += 1
            vertical_offset += 1
        else:
            # screen.addstr((self.y + self.height) // 2, 
            #               ((self.x + self.width) // 2) - (len("No file selected") // 2), 
            #               "No file selected")
            message = "No file to display"
            l = line((self.x + self.width) // 2 - len(message) // 2, 
                     (self.y + self.height) // 2, 
                     message)
            self.lines.append(l)

        for l in self.lines:
            if l.y > self.height - 1:
                break
            screen.addstr(l.y, l.x, l.line)

    def get_signal(self, command):
        return

def test_card():
    from models import Product
    card = ViewCard(Product("example"))
    assert card.description == "example"

def test_window():
    window = Window("Example", 10, 15)
    assert window.title == "Example"
    assert (window.term_width, window.term_height) == (10, 15) 
