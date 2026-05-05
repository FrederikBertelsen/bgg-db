

import os


def clear_cache_folder() -> None:
    print("\nClearing cache folder...\n")
    path = "data/cache"
    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)