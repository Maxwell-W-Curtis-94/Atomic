import os
import shutil
from pathlib import Path

from platformdirs import user_data_dir

from models.distraction_app import DistractionApp

app_data_path = user_data_dir(appname="Atomic", appauthor="Maxwell")

def find_link_file(distraction_app: DistractionApp):
    target_file = distraction_app.shortcuts.original_path
    if os.path.exists(target_file) and not distraction_app.shortcuts.hidden:
        move_link_file(distraction_app.shortcuts.hidden, distraction_app.shortcuts.original_path)


def move_link_file(is_hidden:bool, original_path:str):
    destination_path = Path(app_data_path).joinpath('shortcuts')
    shutil.move(original_path, destination_path)
    with open(app_data_path.join('config.json')) as f:

        pass


def return_link_file():
    pass
