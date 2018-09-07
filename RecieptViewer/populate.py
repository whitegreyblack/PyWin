import sys
import yaml
import strings as log
from database import Connection
from checker import YamlChecker
from wrapper import logger, exitter


# used for exit system message at end of program
exc_err = False


@logger(log.pop['sql_conn'])
def conn_func(*args):
    return Connection()


@logger(log.pop['yml_load'])
def load_func(file, data):
    return yaml.load(data)


@logger(log.pop['sys_read'])
def read_func(file, fin):
    return fin.read()


@logger(log.pop['sys_open'])
def open_func(file):
    with open(file, 'r') as f:
        return read_func(file, f)


@logger(log.pop['sql_push'])
def push_func(file, conn, head, body):
    conn.insert(head, body)


@exitter(log.pop['sys_exit_err'], log.pop['sys_exit_nrm'])
def Populate(folder, files):
    con = conn_func()
    for file in files:
        dat = open_func(folder + file)
        obj = load_func(folder + file, dat)
        obj.hash()
        h, b = obj.build()
        push_func(file, con, h, b)
    filecount, totals = con.stats()
    return filecount, totals


if __name__ == "__main__":
    if len(sys.argv) < 2:
        exit("Incorrect Args - Unspecified Folder")
    folder = sys.argv[1].replace("\\", "/")
    if "/" not in folder:
        folder = folder + "/"
    files, _ = YamlChecker(folder).files_safe()
    Populate(folder, files)