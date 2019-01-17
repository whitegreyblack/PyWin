"""Application.py: 
Main class that builds all other objects and runs the curses loop
"""
import os
import yaml
import math
import random
import curses
import logging
import datetime
import cerberus
from source.keymap import EventMap
import source.utils as utils
import source.config as config
from source.logger import Loggable
from source.controllers import (
    PersonController,
    ExplorerController,
    NotesController,
    ReceiptController
)
from source.schema import (
    Table, 
    SQLType, 
    build_products_table,
    build_receipts_table
)
from source.yamlchecker import YamlChecker
from source.database import (
    Connection,
    NoteConnection,
    ReceiptConnection
)
from source.models.models import Receipt, Transaction, Task, Text
from source.models.product import Product
from source.YamlObjects import receipt as Yamlreceipt
from source.window import (
    Window,
    WindowProperty,
    ScrollableWindow,
    PromptWindow,
    DisplayWindow,
    on_keypress_down,
    on_keypress_up
)

class Application(Loggable):
    """
    Builds the initial parent window using the initial curses screen passed in
    during initialization.

    Also saves export folder paths for data exporting.

    During build functions, creates window objects for the view, controller
    objects to retrieve data after requests are sent in, and moves model data
    into the correct window object.

    Then the application is looped to draw the views onto the screen using 
    curses framework.

    Handles two way data exchanges between windows if data needs transformation
    before reaching destination window from source window.
    """
    def __init__(self, folder, screen=None, logger=None):
        super().__init__(self, logger=logger)
        
        self.continue_app = True
        
        self.screen = screen
        self.window = Window(
            screen, 
            eventmap=EventMap.fromkeys((
                27,         # escape key
                113,        # letter q
                81          # letter Q
            ))
        )
        self.focused = self.window
        self.window.add_handler(27, self.on_keypress_escape)
        self.folder = folder
        self.export = "./export/"

        self.controller = None

        self.data_changed_event = utils.Event()
        self.events = EventMap.fromkeys((
            # curses.KEY_DOWN,
            # curses.KEY_UP,
            # ord('\t'),
            # curses.KEY_BTAB
        ))
        # self.events = {
        #     curses.KEY_DOWN: utils.Event(),
        #     curses.KEY_UP: utils.Event(),
        #     ord('\t'): utils.Event(),
        #     curses.KEY_BTAB: utils.Event()
        # }

    def setup(self):
        # TODO: need a setting to determine behavior of previously loaded data
        # TODO: need a way to format paths before creating other objects
        self.formatted_import_paths = None
        self.formatted_export_path = None
        self.setup_database()

    def setup_database(self):
        self.database.rebuild_tables()
        inserted = self.database.previously_inserted_files()

        files = self.check_files(skip=inserted)
        yobjs = self.load_files(files)
        # self.checker.verify_file_states(loaded_files=inserted)
        # files = self.checker.verified_files

        self.database.insert_files(yobjs)
        self.log(f"Committed:")
        for commit in files:
            self.log(f"+ {commit}")

    def check_files(self, skip=None):
        filestates = []
        if not self.folder:
            return filestates
        for _, _, files in os.walk(self.folder):
            self.log(f"Validating {len(files)} files")
            
            for file_name in files:
                if skip and file_name in skip:
                    continue
                filename, extension = utils.filename_and_extension(file_name)
                self.check_file_name(filename)
                self.check_file_data(file_name)
                filestates.append(file_name)
        return filestates

    def check_file_name(self, filename):
        schema = {
            'filename': {
                'type': 'string', 
                'regex': config.YAML_FILE_NAME_REGEX
            }
        }
        v = cerberus.Validator(schema)
        if not v.validate({'filename': filename}):
            raise BaseException(f'Yaml Filename {filename} is invalid')

    def check_file_data(self, filename):
        v = utils.validate_from_path(
            self.folder + filename,
            './data/schema.yaml'
        )
        if not v:
            raise BaseException(f"File data for {filename} invalid")

    def load_files(self, files):
        yobjs = {}
        for f in files:
            with open(self.folder + f, 'r') as o:
                yobjs[f] = yaml.load(o.read())
        return yobjs

    def run(self):
        while self.continue_app:
            key = self.screen.getch()
            print(self.focused, self.focused.eventmap)
            if key in self.focused.eventmap.keys():
                self.focused.handle_key(key)
                # self.focused.eventmap[key]()
            # if key in self.keymap.keys():
            #     if self.keymap[key] == None:
            #         break
            #     self.keyhandler(key)
            # elif key in self.events.keys():
            #     self.events[key](key)
            else:
                retval = self.send_signal(key)
                if not retval:
                    break
            self.screen.erase()
            self.draw()
            y, x = self.screen.getmaxyx()
            self.screen.addstr(y-1, 1, str(key))

    def keyhandler(self, key):
        self.keymap[key]()

    def build_receipts_for_export(self):
        """Generates Yaml receipt objects from database"""

        # TODO: adding a serialize function in Yamlreceipt will help
        #       shorten this function
        for r in self.database.select_receipts():
            products = {
                p.product: p.price
                    for p in self.database.select_receipt_products(r.filename)
            }

            # separates date into list of int values again
            datelist = utils.parse_date_from_database(r.date)

            # reuse yaml object to export
            receipt = Yamlreceipt(
                r.store, 
                r.short, 
                datelist, 
                r.category, 
                products, 
                r.subtotal, 
                r.tax, 
                r.total,
                r.payment
            )
            yield (r.filename, receipt)

    def export_receipts(self):
        """Should create a folder that matches exactly the input folder"""
        # TODO: single file to hold all data vs multiple files
        # TODO: move file/folder existance checks to self.setup(). That way
        #       the export folder can be checked/created only once and not
        #       every time this function is called
        # verify folder exists. If not then create it
        exportpath = utils.format_directory_path(self.export)
        folderpath = utils.check_or_create_folder(self.export)
        formatpath = utils.format_directory_path(folderpath)
        self.log(f"Begin exporting to {formatpath}")
        for filename, receipt in self.build_receipts_for_export():
            filepath = formatpath + filename + config.YAML_FILE_EXTENSION
            with open(filepath, 'w') as yamlfile:
                yamlfile.write(yaml.dump(receipt))
        self.log("Finished exporting.")

    def generate_reports(self):
        """
        Basically does a join on all the files in the database for common
        data comparisons. Could use a handler to generate all the reports
        specific to the database being used.
        """
        pass

    def build_receipt_viewer(self, rebuild=False):
        screen = self.screen
        height, width = screen.getmaxyx()

        self.controller = ReceiptController(ReceiptConnection(rebuild=rebuild))

        self.data = list(self.controller.request_receipts())

        receipt_explorer = ScrollableWindow(
            screen.subwin(
                height - 2,
                utils.partition(width, 3, 1),
                1,
                0
            ),
            title="receipt",
            title_centered=True,
            focused=True,
            data=[n.store for n in self.data],
            data_changed_handlers=(self.on_data_changed,)
        )
        receipt_explorer.keypress_up_event = on_keypress_up
        receipt_explorer.keypress_down_event = on_keypress_down
        self.window.add_window(receipt_explorer)
        self.events[curses.KEY_DOWN].append(receipt_explorer.handle_key)
        self.events[curses.KEY_UP].append(receipt_explorer.handle_key)

        self.focused = self.window.currently_focused
        if not self.focused:
            self.focused = self.window
        
    """
    def build_windows3(self, screen):
        height, width = screen.getmaxyx()
        self.screen = screen
        self.window = Window('Application', width, height)  
        v1 = View(screen.subwin(1, width, 0, 0))
        optbar = OptionsBar(v1.width)
        v1.add_element(optbar)
        file_options = OptionsList(screen, ("longoption", "shortopt"))
        optbar.add_option('File', file_options)
        optbar.add_option('Edit', None)
        optbar.add_option('Select', None)
        optbar.add_option('Help', None)
        self.window.add_view(v1)
    def build_windows2(self):
        screen = self.screen
        y, x = screen.getbegyx() # just a cool way of getting 0, 0
        height, width = screen.getmaxyx()
        # TODO: options manager, view manager, component manager
        self.window = Window('Application', width, height)

        v1 = View(screen.subwin(height - 1, width, 1, 0), columns=2, rows=2)

        receipt_cards = [ Card(r) for r in self.build_receipts() ]
        scroller = ScrollList(v1.x, v1.y, v1.width // 4, v1.height)
        scroller.add_items(receipt_cards)

        form = receiptForm(
            v1.width // 4,
            v1.y,
            (v1.width // 4) * 3,
            v1.height, scroller.model
        )

        v1.add_element(scroller)
        v1.add_element(form)
        # v2 = View(1, 1, width, height - 1)

        optionview1 = View(screen.subwin(4, 14, 1, 0))
        optionview2 = View(screen.subwin(4, 15, 1, 6))
        optionview3 = View(screen.subwin(4, 15, 1, 12))
        self.window.add_view(v1)
        self.window.add_view(optionview1)
        self.window.add_view(optionview2)
        self.window.add_view(optionview3)
        #self.window.add_view(View(1, 1, width, height - 1))
    """

    def on_focus_changed(self, sender, arg=None):
        self.focused = self.window.currently_focused

    def on_data_changed(self, sender, arg):
        model = self.data[arg]
        self.data_changed_event(sender, model)

    def on_keypress_escape(self, sender, arg=None):
        self.continue_app = False

    def build_file_explorer(self):
        """Work on putting folder/file names in window"""
        screen = self.screen
        height, width = screen.getmaxyx()
        self.controller = ExplorerController()
        self.data = [
            self.controller.request_tree()
        ]

    def build_todo_tasks(self):
        """Builds a todo app"""
        screen = self.screen
        height, width = screen.getmaxyx()

        self.data = [
            Task(f"task {i}", random.randint(0, 3), datetime.datetime.today())
                for i in range(50)
        ]

        self.window.title = "Tasks To Do"

        task_win = DisplayWindow(
            screen.subwin(
                utils.partition(height-2, 2, 1),
                width,
                utils.partition(height, 2, 1),
                0
            )
        )
        self.data_changed_event.append(task_win.on_data_changed)

        none_win = ScrollableWindow(
            screen.subwin(
                (height // 2) - 1,
                utils.partition(width, 4, 1),
                1, 
                0
            ),
            title="No Status",
            title_centered=True,
            data=[task.title for task in self.data if task.status_id == 0],
            data_changed_handlers=(self.on_data_changed,)
        )

        todo_win = ScrollableWindow(
            screen.subwin(
                (height // 2) - 1,
                utils.partition(width, 4, 1),
                1,
                utils.partition(width, 4, 1)
            ),
            title="Todo",
            title_centered=True,
            focused=True,
            data=[task.title for task in self.data if task.status_id == 1],
            data_changed_handlers=(self.on_data_changed,),
            eventmap=EventMap.fromkeys((
                ord('\t'),          # 9
                curses.KEY_BTAB,    # 351
                curses.KEY_DOWN,    # 258
                curses.KEY_UP,      # 259
                27
            ))
        )

        work_win = ScrollableWindow(
            screen.subwin(
                (height // 2) - 1,
                utils.partition(width, 4, 1),
                1,
                utils.partition(width, 4, 2)
            ),
            title="In-progress",
            title_centered=True,
            data=[task.title for task in self.data if task.status_id == 2],
            data_changed_handlers=(self.on_data_changed,)
        )

        done_win = ScrollableWindow(
            screen.subwin(
                (height // 2) - 1,
                utils.partition(width, 4, 1),
                1,
                utils.partition(width, 4, 3)
            ),
            title="Finished",
            title_centered=True,
            data=[task.title for task in self.data if task.status_id == 3],
            data_changed_handlers=(self.on_data_changed,)
        )

        none_win.add_handler(258, on_keypress_down)
        none_win.add_handler(259, on_keypress_up)
        none_win.add_handler(27, self.on_keypress_escape)
        none_win.add_handlers(9, (
            none_win.unfocus,
            todo_win.focus, 
            self.on_focus_changed
        ))
        todo_win.add_handler(258, on_keypress_down)
        todo_win.add_handler(259, on_keypress_up)
        todo_win.add_handler(27, self.on_keypress_escape)
        todo_win.add_handlers(351, (
            todo_win.unfocus,
            none_win.focus, 
            self.on_focus_changed
        ))
        todo_win.add_handlers(9, (
            todo_win.unfocus,
            work_win.focus, 
            self.on_focus_changed
        ))

        work_win.add_handler(258, on_keypress_down)
        work_win.add_handler(259, on_keypress_up)
        work_win.add_handler(27, self.on_keypress_escape)
        work_win.add_handlers(351, (
            work_win.unfocus,
            todo_win.focus, 
            self.on_focus_changed
        ))
        work_win.add_handlers(9, (
            work_win.unfocus,
            done_win.focus, 
            self.on_focus_changed
        ))

        done_win.add_handler(258, on_keypress_down)
        done_win.add_handler(259, on_keypress_up)
        done_win.add_handler(27, self.on_keypress_escape)
        done_win.add_handlers(351, (
            done_win.unfocus,
            work_win.focus, 
            self.on_focus_changed
        ))

        self.window.add_windows(
            none_win,
            todo_win,
            work_win,
            done_win,
            task_win
        )

        self.focused = self.window.currently_focused

    def build_note_viewer(self, rebuild=False):
        """Builds an application to view all notes"""
        screen = self.screen
        height, width = screen.getmaxyx()

        self.controller = NotesController(NoteConnection(rebuild=rebuild))
        self.data = self.controller.request_notes()

        self.window.title = 'Note Viewer Example'

        note_display = DisplayWindow(
            screen.subwin(
                height - 2,
                utils.partition(width, 3, 2),
                1,
                utils.partition(width, 3, 1)
            )
        )
        self.data_changed_event.append(note_display.on_data_changed)
        self.window.add_window(note_display)

        note_explorer_props = WindowProperty({
            'title': "Notes",
            'title_centered': True,
            'focused': True,            
        })
        note_explorer = ScrollableWindow(
            screen.subwin(
                height - 2,
                utils.partition(width, 3, 1),
                1,
                0
            ),
            title="Notes",
            title_centered=True,
            focused=True,
            data=[n.title for n in self.data],
            data_changed_handlers=(self.on_data_changed,)
        )
        note_explorer.keypress_up_event = on_keypress_up
        note_explorer.keypress_down_event = on_keypress_down
        self.window.add_window(note_explorer)
        self.events[curses.KEY_DOWN].append(note_explorer.handle_key)
        self.events[curses.KEY_UP].append(note_explorer.handle_key)

        help_window = DisplayWindow(
            screen.subwin(
                height - 12,
                utils.partition(width, 4, 2),
                6,
                utils.partition(width, 4, 1)
            ),
            title="Help",
            dataobj=Text.random(),
            showing=False,
        )
        help_window.add_handler(ord('h'), help_window.toggle_showing)
        self.events[ord('h')].append(help_window.handle_key)
        self.window.add_window(help_window)

        self.focused = self.window.currently_focused

    def build_note_viewer_with_properties(self):
        pass

    def build_windows1(self):
        """Work on window recursion and tree"""
        screen = self.screen
        height, width = screen.getmaxyx()
        self.controller = PersonController()
        self.data = [
            self.controller.request_person(pid)
                for pid in range(10)
        ]
        # main window
        self.window.title = 'Application Example 1'

        # display window
        display = DisplayWindow(
            screen.subwin(
                11,
                utils.partition(width, 5, 3),
                1, 
                utils.partition(width, 5, 2)
            ),
            title="Profile"
        )
        self.data_changed_event.append(display.on_data_changed)

        # scroll window
        scroller = ScrollableWindow(
            screen.subwin(
                height - 2, 
                utils.partition(width, 5, 2), 
                1, 
                0
            ),
            title="Directory",
            data=[str(n.name) for n in self.data],
            focused=True,
            data_changed_handlers=(self.on_data_changed,)
        )

        # secondary display -- currently unused
        # adding sub windows to parent window
        unused = Window(
            screen.subwin(
                height - 13, 
                utils.partition(width, 5, 3),
                12, 
                utils.partition(width, 5, 2)
            ), 
            title='verylongtitlescree'
        )

        # prompt screen
        prompt = PromptWindow(screen.subwin(3, width, height - 4, 0))

        self.window.add_windows([
            scroller,
            display,
            unused,
            prompt
        ])

        # add window key handlers to application event mapping
        self.events[curses.KEY_DOWN].append(scroller.handle_key)
        self.events[curses.KEY_UP].append(scroller.handle_key)

    def build_windows(self):
        """Work on window recursion and tree"""
        screen = self.screen
        height, width = screen.getmaxyx()
        self.controller = PersonController()
        self.data = [
            self.controller.request_person(pid)
                for pid in range(10)
        ]

        # main window
        self.window = Window(screen, title='Application Example 1')

        # display window
        display = DisplayWindow(
            screen.subwin(
                11,
                utils.partition(width, 5, 3),
                1, 
                utils.partition(width, 5, 2)
            ),
            title="Profile"
        )
        self.data_changed_event.append(display.on_data_changed)

        # scroll window
        scroller = ScrollableWindow(
            screen.subwin(
                height - 2, 
                utils.partition(width, 5, 2), 
                1, 
                0
            ),
            title="Directory",
            data=[str(n.name) for n in self.data],
            focused=True,
            data_changed_handlers=(self.on_data_changed,)
        )
        scroller.keypress_up_event.append(on_keypress_up)
        scroller.keypress_down_event.append(on_keypress_down)
        # secondary display -- currently unused
        # adding sub windows to parent window
        unused = Window(
            screen.subwin(
                height - 13, 
                utils.partition(width, 5, 3),
                12, 
                utils.partition(width, 5, 2)
            ), 
            title='verylongtitlescree'
        )

        # prompt screen
        prompt = PromptWindow(screen.subwin(3, width, height - 4, 0))

        self.window.add_windows([
            scroller,
            display,
            unused,
            prompt
        ])

        # add window key handlers to application event mapping
        self.events[curses.KEY_DOWN].append(scroller.handle_key)
        self.events[curses.KEY_UP].append(scroller.handle_key)

        # v1 = View(screen.subwin(height - 1, width, 1, 0), columns=2, rows=2)
        # self.window.add_view(v1)

        # scroller = ScrollList(1, 1,
        #                       self.window.width // 4,
        #                       self.window.height,
        #                       title='receipts',
        #                       selected=True)

        # receipt_cards = [ Card(r) for r in self.build_receipts() ]
        # scroller.add_items(receipt_cards)
        # form = receiptForm(
        #     (self.window.width // 4) + 1, # add 1 for offset
        #     1,
        #     self.window.width - (self.window.width // 4) - 1, 
        #     self.window.height,
        #     scroller.model
        # )

        # promptwin = screen.subwin(
        #     self.window.height // 3, 
        #     self.window.width // 2, 
        #     self.window.height // 3,
        #     self.window.width // 4
        # )

        # exitprompt = Prompt(
        #     promptwin, 
        #     'Exit Prompt', 
        #     'Confirm', 
        #     'Cancel', 
        #     logger=self.logger
        # )

        # self.window.add_windows([scroller, form, exitprompt])

        keymap = dict()
        keymap[(curses.KEY_DOWN, 1)] = 1
        # keymap[(curses.CTL_ENTER)] -- prompt control CTRLEnter: show/hide, ENTER: command
        # keymap[(curses.KEY_UP, scroller.wid)] = scroller.wid
        # keymap[(curses.KEY_DOWN, scroller.wid)] = scroller.wid
        # keymap[(curses.KEY_ENTER, scroller.wid)] = form.wid
        # keymap[(curses.KEY_RIGHT, scroller.wid)] = form.wid
        # keymap[(curses.KEY_LEFT, form.wid)] = scroller.wid
        # keymap[(curses.KEY_LEFT, exitprompt.wid)] = exitprompt.wid
        # keymap[(curses.KEY_RIGHT, exitprompt.wid)] = exitprompt.wid
        # keymap[(ord('\t'), exitprompt.wid)] = exitprompt.wid
        # # keymap[(curses.KEY_F1,)] = 'receipts'
        # # 10 : New Line Character
        # keymap[(10, scroller.wid)] = form.wid
        # keymap[(10, exitprompt.wid)] = scroller.wid
        # # 27 : Escape Key Code
        # keymap[(27, scroller.wid)] =  exitprompt.wid
        # keymap[(27, exitprompt.wid)] = None
        # keymap[(27, form.wid)] = scroller.wid
        # keymap[(ord('y'), exitprompt.wid)] = None
        # keymap[(ord('n'), exitprompt.wid)] = form.wid
        # keymap[(curses.KEY_ENTER, exitprompt.wid)] = None
        self.window.add_keymap(keymap)

    def draw(self):
        # self.screen.addstr(0, 0, ' ' * (self.window.width + 2), curses.color_pair(2))
        # self.screen.insstr(self.window.height + 1,
        #                    0,
        #                    ' ' * (self.window.width + 2),
        #                    curses.color_pair(3))
        # self.screen.addstr(0, 1, "File", curses.color_pair(2))
        # self.screen.addstr(0, 7, "Edit", curses.color_pair(2))
        # self.screen.addstr(0, 13, "Selection", curses.color_pair(2))

        # self.screen.addstr(1, 2, "Options:")
        # self.screen.addstr(2, 2, "[e] export files")
        # self.screen.addstr(4, 2, "[E] export current file")

        # self.screen.addstr(2, self.window.width // 8, "[receipts]")
        # self.screen.addstr(2, self.window.width // 8 + 11, "[Products]")
        # self.screen.addstr(2, self.window.width // 8 + 22, "[Stores]")
        # self.window.draw(self.screen)

        if not self.window:
            raise Exception("No window to draw")

        # send in the screen to all window objects
        if self.window.showing:
            self.window.draw()

    def send_signal(self, signal):
        return self.window.send_signal(signal)

if __name__ == "__main__":
    a = Application('./receipts/')
    a.setup()
    a.build_windows()
    a.run()
    for table in a.database.tables:
        print(table)
