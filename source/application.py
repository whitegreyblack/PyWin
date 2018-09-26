import curses
import logging
import datetime

import source.utils as utils
import source.config as config
from source.logger import Loggable
from source.schema import Table
from source.utils import SQLType
from source.yamlchecker import YamlChecker
from source.database import Connection
from source.models.models import Reciept, Transaction
from source.models.product import Product
from source.controls import Window, ScrollList, Card, RecieptForm, Prompt, Button

def setup_test_cards():
    """List of example product cards used in testing"""
    return [Card(Product(fruit, price))
            for fruit, price in zip(
                ['Apples', 'Oranges', 'Pears', 'Watermelons', 'Peaches'],
                [3, 5, 888, 24, 55])]

class Application(Loggable):
    """Overview:
    Buids the database and yamlchecker objects. (They are tightly coupled. May
    need to change in the future.) The data from the yaml files found in using
    the folder path paramter are first checked by the yamlchecker before
    loading into the database.

    With loading finished, the front end is created and views are initialized,
    using data from the database.

    Then the application is looped to draw the views onto the screen using 
    curses framework.
    """
    def __init__(self, folder, logger, rebuild=False):
        super().__init__(self, logger=logger)

        self.checker = YamlChecker(folder, logger=logger)

        tables = [
            Table("reciepts",
                  [
                    ("filename", SQLType.TEXT),
                    ("store", SQLType.VARCHAR()),
                    ("short", SQLType.TEXT),
                    ("date", SQLType.VARCHAR(10)), 
                    ("category", SQLType.VARCHAR()),
                    ("subtotal", SQLType.REAL),
                    ("tax", SQLType.REAL),
                    ("total", SQLType.REAL),
                    ("payment", SQLType.REAL)
                  ], unique=["filename",]
            ),
            Table("products", 
                  [
                    ("filename", SQLType.TEXT),
                    ("product", SQLType.VARCHAR()),
                    ("price", SQLType.REAL)
                  ], unique=["filename", "product", "price"]
            )
        ]

        self.database = Connection(tables, logger=logger, rebuild=rebuild)

    def setup(self):
        # TODO: need a setting to determine behavior of previously loaded data
        self.database.rebuild_tables()
        inserted = self.database.inserted_files()

        self.checker.verify_file_states(loaded_files=inserted)
        files = self.checker.verified_files

        self.database.insert_files(files)
        self.log(f"Committed:")
        for commit in files:
            self.log(f"+ {commit}")

    def build_reciepts(self):
        reciepts = []
        for rdata in self.database.select_reciepts():
            reciept = rdata.filename
            rproducts = list(self.database.select_reciept_products(reciept))
            t = Transaction(rdata.total, rdata.payment, 
                            rdata.subtotal, rdata.tax)

            d = utils.format_database_date(rdata.date)
            r = Reciept(rdata.store,
                        rdata.short,
                        utils.format_date(d, config.DATE_FORMAT['L']),
                        utils.format_date(d, config.DATE_FORMAT['S']),
                        rdata.category,
                        [Product(p.product, p.price) for p in rproducts], t)
            reciepts.append(r)
        return reciepts

    def build_windows(self, screen):
        height, width = screen.getmaxyx()
        self.window = Window('Application', width, height)
        
        scroller = ScrollList(1, 1,
                              self.window.width // 4,
                              self.window.height,
                              'Reciepts',
                              selected = True)

        reciepts = self.build_reciepts()
        reciept_cards = [Card(r) for r in reciepts]
        scroller.add_items(reciept_cards)
        form = RecieptForm((self.window.width // 4) + 1, # add 1 for offset
                           1,
                           self.window.width - (self.window.width // 4) - 1, 
                           self.window.height,
                           scroller.model)
    
        subwin = screen.subwin(self.window.height // 3, 
                               self.window.width // 2, 
                               self.window.height // 3,
                               self.window.width // 4)

        exitprompt = Prompt(subwin, 'Exit Prompt', 'Confirm', 'Cancel', logger=self.logger)

        self.window.add_windows([scroller, form, exitprompt])

        keymap = dict()
        keymap[(curses.KEY_UP, scroller.wid)] = scroller.wid
        keymap[(curses.KEY_DOWN, scroller.wid)] = scroller.wid
        keymap[(curses.KEY_ENTER, scroller.wid)] = form.wid
        keymap[(curses.KEY_RIGHT, scroller.wid)] = form.wid
        keymap[(curses.KEY_LEFT, form.wid)] = scroller.wid
        keymap[(curses.KEY_LEFT, exitprompt.wid)] = exitprompt.wid
        keymap[(curses.KEY_RIGHT, exitprompt.wid)] = exitprompt.wid
        keymap[(ord('\t'), exitprompt.wid)] = exitprompt.wid
        # keymap[(curses.KEY_F1,)] = 'Reciepts'
        # 10 : New Line Character
        keymap[(10, scroller.wid)] = form.wid
        keymap[(10, exitprompt.wid)] = scroller.wid
        # 27 : Escape Key Code
        keymap[(27, scroller.wid)] =  exitprompt.wid
        keymap[(27, exitprompt.wid)] = None
        keymap[(27, form.wid)] = scroller.wid
        keymap[(ord('y'), exitprompt.wid)] = None
        keymap[(ord('n'), exitprompt.wid)] = form.wid
        keymap[(ord('q'), scroller.wid)] = None
        keymap[(curses.KEY_ENTER, exitprompt.wid)] = None
        self.window.add_keymap(keymap)

    def draw(self, screen):
        self.window.draw(screen)

    def send_signal(self, signal):
        return self.window.send_signal(signal)

if __name__ == "__main__":
    pass