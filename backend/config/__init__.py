# Lets Django use MySQL through the PyMySQL driver.
try:
    import pymysql
    pymysql.version_info = (2, 2, 1, "final", 0)  # newer Django checks this number
    pymysql.install_as_MySQLdb()
except ImportError:
    pass