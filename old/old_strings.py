"""Strings.py: DEPRACATED. Strings moved to statements.py"""
# -----------------------------------------------------------------------------
# AUTHOR: Sam Whang
# FILE  : STRINGS.PY
# FORUSE: STARTUP DURING FILE/YAML CHECKING
# MORE  : (INFO|DEBUG|WARNING) [TRY|ERROR|SUCCESS] STRINGS FOR LOGGER
# -----------------------------------------------------------------------------
pop = {
    'sql_populate': "-- LOGGER :- Populate() --",
    'sql_frontend': "-- LOGGER :- FrontEnd() --",

    'sql_conn': (
        "SQL: Creating Connection",
        "SQL: Connection Error ",
        "SQL: Connection Established",
    ),

    'sql_conn_cls': "SQL: Connection Close",

    'sql_push': (
        "SQL: Table Write Head and Body for [{}]",
        "SQL: Table Write Error",
        "SQL: Table Write Success",
    ),

    'yml_load': (
        "YML: Load Data [{}]",
        "YML: Load Data Error",
        "YML: Load Data Success",
    ),

    'sys_exit_nrm': "SYS: Exiting Application Normally",
    'sys_exit_err': "SYS: Exiting Application Early",

    'sys_read': (
        "SYS: Read File [{}]",
        "SYS: Read File Error",
        "SYS: Read File Success",
    ),

    'sys_open': (
        "SYS: Open File [{}]",
        "SYS: Open File Error",
        "SYS: Open File Success",
    ),

    'sql_slct_all': "SQL: Select",
    'sql_slct_try': "SQL: Select {}={}",
    'sql_slct_err': "SQL: Select Error",
    'sql_slct_scs': "SQL: Select Success",
}
# -----------------------------------------------------------------------------
# FORUSE: USED IN CHECKER FOR PRINT OUTPUT TO LOGGER AND STDOUT
# MORE  : USES TERMINAL COLOR CODES FOR COLORED OUTPUT (PASS=GREEN|FAIL=RED)
# -----------------------------------------------------------------------------
ORG = '\x1b[0;34;40m'
YEL = '\x1b[0;33;40m'
GRN = '\x1b[1;32;40m'
RED = '\x1b[1;31;40m'
END = '\x1b[0m'
passfail = {
    'file_safe': {
        True: GRN + ("File Pass") + END,
        False: RED + ("File Fail") + END,
    },
    'file_regex': {
        True: GRN + ("Regx Pass") + END,
        False: RED + ("Regx Fail") + END,
    },
    'file_read': {
        True: GRN + ("Read Pass") + END,
        False: RED + ("Read Fail") + END
    },
    'file_load': {
        True: GRN + ("Load Pass") + END,
        False: RED + ("Load Fail") + END,
    },
    'store_test': {
        True: GRN + ("Store Pass") + END,
        False: RED + ("Store Fail") + END,
    },
    'yaml_safe': {
        True: GRN + ("Yaml Pass") + END,
        False: RED + ("Yaml Fail") + END,
    },
    'yaml_read': {
        True: GRN + ("Read Pass") + END,
        False: RED + ("Read Fail") + END,
    },
    'yaml_store': {
        True: GRN + ("Name Pass") + END,
        False: RED + ("Name Fail") + END,
    },
    'yaml_date': {
        True: GRN + ("Date Pass") + END,
        False: RED + ("Date Fail") + END,
    },
    'yaml_prod': {
        True: GRN + ("Prod Pass") + END,
        False: RED + ("Prod Fail") + END,
    },
    'yaml_card': {
        True: GRN + ("Card Pass") + END,
        False: RED + ("Card Fail") + END,
    }
}
# -----------------------------------------------------------------------------
# FORUSE: USED IN DATABASE CONNECTION DURING STARTUP AND RUNTIME
# MORE  : SQL COMMANDS FOR DATA BASE INSERTION|SELECTION|MODIFICATION|DELETION
# -----------------------------------------------------------------------------
stmts = {
    'headcreate': """create table if not exists receipthead (store varchar(25),
        date varchar(10), type varchar(10), code varchar(30) PRIMARY KEY,
        subtotal real, tax real, total real, UNIQUE(store, date, total))""",
    'headinsert': """insert or ignore into receipthead \
            values (?,?,?,?,?,?,?);""",

    'bodycreate': """create table if not exists receiptbody (item varchar(25),
        price real, code varchar(30), UNIQUE(item, price, code))""",
    'bodyinsert': """insert or ignore into receiptbody values (?,?,?)""",

    'filecount': """select count(*) from receipthead""",
    'total': """select sum(total) from receipthead""",

    'algrocery': """select * from receipthead""",
    'hdgrocery': """select * from receipthead where {}='{}'""",
    'bdgrocery': """select * from receipthead where code={}""",

    'mindate': """select min(date) from receipthead""",
    'maxdate': """select max(date) from receipthead""",
}
