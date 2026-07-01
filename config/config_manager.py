import logging
import shutil
from pathlib import Path
from platformdirs import user_data_dir

logger = logging.getLogger(__name__)



def initialize():
    logging.info("Loading config")
    app_data_path = user_data_dir(appname="Atomic", appauthor="Maxwell")
    path = Path(app_data_path)
    path.mkdir(parents=True, exist_ok=True)
    logging.info("App folder created")
    logging.debug("App folder path: {}".format(path))
    source_file = "config/default_config.json"
    destination_path = path.joinpath("config.json")
    if not destination_path.exists():
        shutil.copyfile(source_file, destination_path)
        logging.info("Config file created")
    else:
        logger.info("Config file loaded")


def save_config():
    #save new config_model to the file system
    pass

def add_distraction_app(distraction_app):
    pass

def remove_distraction_app(distraction_app):
    pass


def add_productive_app(product_app):
    pass


def remove_productive_app(product_app):
    pass

def add_schedule(datetime):
    pass

def remove_schedule(schedule_id):
    pass
