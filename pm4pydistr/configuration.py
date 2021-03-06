import os
import socket

ENVIRON_PREFIX = "pm4pydistr"
PARAMETERS_AUTO_HOST = "autohost"
PARAMETERS_AUTO_PORT = "autoport"

PARAMETER_USE_TRANSITION = "use_transition"
DEFAULT_USE_TRANSITION = False
PARAMETER_NO_SAMPLES = "no_samples"
DEFAULT_MAX_NO_SAMPLES = 10000000
PARAMETER_START = "start"
PARAMETER_WINDOW_SIZE = "window_size"
PARAMETER_NUM_RET_ITEMS = "num_ret_items"
DEFAULT_WINDOW_SIZE = 500

PARAMETER_PM4PYWS_CLASSIFIER = "@@classifier"

KEYPHRASE = "hello"
if str(os.name) == "posix":
    PYTHON_PATH = "python3"
else:
    PYTHON_PATH = "python"
BASE_FOLDER_LIST_OPTIONS = ["master"]
#BASE_FOLDER_LIST_OPTIONS = ["master", "/opt/pm4pydistr-share"]

DEFAULT_TYPE = "slave"
THIS_HOST = socket.gethostbyaddr(socket.gethostname())[2][0]
PORT = 5001
MASTER_HOST = '137.226.117.71'
MASTER_PORT = 5001
CONF = "local"

PARAMETERS_TYPE = "type"
PARAMETERS_PORT = "port"
PARAMETERS_MASTER_HOST = "masterhost"
PARAMETERS_MASTER_PORT = "masterport"
PARAMETERS_CONF = "conf"
PARAMETERS_HOST = "host"
PARAMETERS_KEYPHRASE = "keyphrase"
PARAMETERS_BASE_FOLDERS = "basefolders"

SLEEPING_TIME = 1
SESSION_EXPIRATION = 70

MAX_RAM = 16000000000
MAX_T_JUNCTION = 100
DEFAULT_K = 10
SIZE_THRESHOLD = 0.5

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
