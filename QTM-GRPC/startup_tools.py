"""
Startup for tool menus. Invoke the add_menu function for scripts found at the top level of the tools folder.
"""
from json import tool
import sys
import os
import inspect
import importlib

# Set scripts 'path' to your repo location
# NOTE: This needs to be done before importing custom libraries
from pathlib import Path
QTM_GRPC_DIR = Path(__file__).resolve().parent
TOOLS_DIR = QTM_GRPC_DIR / "tools"
USERS_DIR = QTM_GRPC_DIR / "users"
USER_DIR = QTM_GRPC_DIR / "user"
HELPERS_DIR = QTM_GRPC_DIR / "helpers"

for _p in (QTM_GRPC_DIR, TOOLS_DIR, USERS_DIR, USER_DIR, HELPERS_DIR):
    if _p.exists() and str(_p) not in sys.path:
        sys.path.append(str(_p))

this_file = str(Path(__file__).resolve())
this_dir = str(QTM_GRPC_DIR)
tools_dir = str(TOOLS_DIR)
user_dir = str(USER_DIR)
import qtm

# NOTE ON ADDING NEW MENU FILES
#
# If you create a new tools menu file just copy it to the tools
# folder.  Make sure it has the module variable 'menu_priority' set 
# to something other than 0 (the larger the value the further
# to the right in the menus it will appear) AND have the add_menu() function which
# creates a QTM menu.  This script will automatically find your file and call the 
# function to make the menu.
#
# Menus with the same priority value will be added in alphabetical order (well, 
# the order in which listdir() returns the file names).
#
# Support for a "user" folder is included.  If a user wishes to keep their own
# custom menus separate from the tools folder then create a "user" folder and put
# the scripts in there.
#
def _add_subfolder(folder, verbose = False):
    try:
        filenames = os.listdir(os.path.join(this_dir,folder))
    except:
        if verbose:
            print(f"{this_file}: Unable to list sub-folder '{folder}', does it exist?")
        return
    menu_files = []
    #print(filenames)
    for filename in filenames:
        if "__" not in filename[0]:
            modname = filename.split('.',1)[0]
            try:
                print(modname)
                mod = importlib.import_module(modname)
                importlib.reload(mod)
            except ModuleNotFoundError as err:
                print(err)
                print(f"{this_file}: Could not load {filename} as a module, skipping...")
            except Exception as e:
                print(e)
                print(f"{this_file}: Exception: {str(e)} in {filename}, skipping...")   
            else:             
                if mod is not None:
                    d = dir(mod)
                    priority_level = 0
                    if 'menu_priority' in d:
                        priority_level = mod.menu_priority
                    if priority_level > 0:
                        if 'add_menu' in d:
                            menu_files.append({'mod': mod, 'modname': modname, 'priority_level': priority_level})
                else:
                    if verbose:
                        print(f"{this_file}: Unable to load {modname}")    
    menu_files.sort(key=lambda x: x['priority_level'])

    for menu_file in menu_files:
        menu_file['mod'].add_menu()
        print(f"Added {menu_file['modname']} menu.")
    
def add_menus():
    _add_subfolder("users",True)
    _add_subfolder("tools",True) 
     

if __name__ == '__main__':
    add_menus()
