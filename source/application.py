__author__ = "Samuel Whang"

import yaml
import curses
import logging
import datetime
import source.utils as utils
import source.config as config
from source.logger import Loggable
from source.schema import (
    Table, SQLType, build_products_table, build_reciepts_table
)
from source.yamlchecker import YamlChecker
from source.database import Connection
from source.models.models import Reciept, Transaction
from source.models.product import Product
from source.YamlObjects import Reciept as YamlReciept
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
    def __init__(self, folder, logger=None, rebuild=False):
        super().__init__(self, logger=logger)
        self.folder = folder
        self.export = "export/"
        self.checker = YamlChecker(folder, logger=logger)

        tables = [
            build_reciepts_table(),
            build_products_table()
        ]

        self.keymap = dict()
        self.keymap[ord('e')] = self.export_reciepts

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

    def run(self):
        while True:
            key = self.screen.getch()
            if key in self.keymap.keys():
                self.keyhandler(key)
            else:
                retval = self.send_signal(key)
                if not retval:
                    break
            self.screen.erase()
            self.draw()

    def keyhandler(self, key):
        self.keymap[key]()

    def build_reciepts(self):
        """Generates View Reciept objects from database"""
        for rdata in self.database.select_reciepts():
            reciept = rdata.filename
            rproducts = list(self.database.select_reciept_products(reciept))
            t = Transaction(rdata.total, rdata.payment, 
                            rdata.subtotal, rdata.tax)

            d = utils.parse_date_from_database(rdata.date)
            r = Reciept(rdata.store,
                        rdata.short,
                        utils.format_date(d, config.DATE_FORMAT['L']),
                        utils.format_date(d, config.DATE_FORMAT['S']),
                        rdata.category,
                        [Product(p.product, p.price) for p in rproducts], t)
            yield r

    def build_reciepts_for_export(self):
        """Generates Yaml Reciept objects from database"""
        for r in self.database.select_reciepts():
            products = {
                p.product: p.price
                    for p in self.database.select_reciept_products(r.filename)
            }

            # separates date into list of int values again
            datelist = utils.parse_date_from_database(r.date)

            # reuse yaml object to export
            reciept = YamlReciept(r.store, r.short, datelist, r.category, 
                                  products, r.subtotal, r.tax, r.total,
                                  r.payment)
            yield (r.filename, reciept)

    def export_reciepts(self):
        """Should create a folder that matches exactly the input folder"""
        # verify folder exists. If not then create it
        exportpath = utils.format_directory_path(self.export)
        folderpath = utils.check_or_create_folder(self.export)
        formatpath = utils.format_directory_path(folderpath)
        self.log(f"Begin exporting to {formatpath}")
        for filename, reciept in self.build_reciepts_for_export():
            filepath = formatpath + filename + config.YAML_FILE_EXTENSION
            with open(filepath, 'w') as yamlfile:
                yamlfile.write(yaml.dump(reciept))
        self.log("Finished exporting.")

    def generate_reports(self):
        """Basically does a join on all the files in the database for common
        data comparisons. Could use a handler to generate all the reports
        specific to the database being used.
        """
        pass

    def build_windows(self, screen):
        self.screen = screen
        height, width = screen.getmaxyx()
        self.window = Window('Application', width, height)
        
        scroller = ScrollList(self.window.width // 8 - 2, 4,
                              self.window.width // 4,
                              self.window.height,
                              'Reciepts',
                              selected = True)

        reciept_cards = [ Card(r) for r in self.build_reciepts() ]
        scroller.add_items(reciept_cards)
        form = RecieptForm((self.window.width // 4) + 1, # add 1 for offset
                           1,
                           self.window.width - (self.window.width // 4) - 1, 
                           self.window.height,
                           scroller.model)
    
        promptwin = screen.subwin(self.window.height // 3, 
                                  self.window.width // 2, 
                                  self.window.height // 3,
                                  self.window.width // 4)

        exitprompt = Prompt(promptwin, 'Exit Prompt', 'Confirm', 'Cancel', logger=self.logger)

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

    def draw(self):
        self.screen.addstr(1, 2, "Options:")
        self.screen.addstr(2, 2, "[e] export files")
        self.screen.addstr(4, 2, "[E] export current file")

        self.screen.addstr(2, self.window.width // 8, "[Reciepts]")
        self.screen.addstr(2, self.window.width // 8 + 11, "[Products]")
        self.screen.addstr(2, self.window.width // 8 + 22, "[Stores]")
        self.window.draw(self.screen)

    def send_signal(self, signal):
        return self.window.send_signal(signal)

if __name__ == "__main__":
    a = Application('data/')
    for table in a.database.tables:
        print(table)