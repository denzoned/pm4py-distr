import os

ENVIRON_PREFIX = "pm4pydistr"
PARAMETERS_AUTO_HOST = "--auto-host"

PARAMETER_USE_TRANSITION = "use_transition"
DEFAULT_USE_TRANSITION = False
PARAMETER_NO_SAMPLES = "no_samples"
DEFAULT_MAX_NO_SAMPLES = 10000000
PARAMETER_NUM_RET_ITEMS = "num_ret_items"
DEFAULT_MAX_NO_RET_ITEMS = 500

KEYPHRASE = "hello"
if str(os.name) == "posix":
    PYTHON_PATH = "python3"
else:
    PYTHON_PATH = "python"
BASE_FOLDER_LIST_OPTIONS = ["master", "/opt/pm4pydistr-share"]

THIS_HOST = "127.0.0.1"
PORT = 5001
MASTER_HOST = "127.0.0.1"
MASTER_PORT = 5001
CONF = "local"

PARAMETERS_TYPE = "--type"
PARAMETERS_PORT = "--port"
PARAMETERS_MASTER_HOST = "--master-host"
PARAMETERS_MASTER_PORT = "--master-port"
PARAMETERS_CONF = "--conf"
PARAMETERS_HOST = "--host"
PARAMETERS_KEYPHRASE = "--keyphrase"
PARAMETERS_BASE_FOLDERS = "--base-folders"

SLEEPING_TIME = 30
SESSION_EXPIRATION = 70
