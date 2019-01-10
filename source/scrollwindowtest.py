import curses
from source.utils import Event
from source.window import ScrollableWindow, on_keypress_up, on_keypress_down

def initialize_curses_settings(logger=None):
    """Sets settings for cursor visibility and color pairings"""
    if logger:
        logger.info('main(): initializing curses library settings')
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_CYAN)

def application(screen):
    events = {
        curses.KEY_UP: Event(),
        curses.KEY_DOWN: Event()
    }
    s = ScrollableWindow(screen, data=[str(i) for i in range(100)])
    s.keypress_up_event.append(on_keypress_up)
    s.keypress_down_event.append(on_keypress_down)
    
    events[curses.KEY_UP].append(s.handle_key)
    events[curses.KEY_DOWN].append(s.handle_key)

    initialize_curses_settings()

    s.draw()
    while True:
        key = screen.getch()
        if key in events.keys():
            events[key](key)
        elif key == 27 or key == ord('q'):
            break
        s.erase()
        s.draw()

def main():
    curses.wrapper(application)

if __name__ == "__main__":
    main()