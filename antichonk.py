import os
import math
import sys
import glob
import json
import shutil
from datetime import datetime
from pathlib import Path
from pathlib import Path

def print_help():
    print("Interactive program to delete files based on certain characteristics")
    print("usage: sudo antichonk.py DIRECTORY(TV|Movies|downloads) ORDER_BY(age|size)")

def ensure_user_is_root():
    if os.geteuid() != 0:
        exit("You need to have root privileges to run this script.\nPlease try again, this time using sudo") 

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class DisplayablePath(object):
    display_filename_prefix_middle = '├──'
    display_filename_prefix_last = '└──'
    display_parent_prefix_middle = '    '
    display_parent_prefix_last = '│   '

    def __init__(self, path, child_to_highlight, parent_path, is_last):
        self.path = Path(str(path))
        self.parent = parent_path
        self.child_to_highlight = child_to_highlight
        self.is_last = is_last
        if self.parent:
            self.depth = self.parent.depth + 1
        else:
            self.depth = 0

    @property
    def displayname(self):
        if self.path.is_dir():
            return self.path.name + '/'
        return self.path.name

    @classmethod
    def make_tree(cls, root, child_to_highlight, parent=None, is_last=False, criteria=None):
        root = Path(str(root))
        criteria = criteria or cls._default_criteria

        displayable_root = cls(root, child_to_highlight, parent, is_last)
        yield displayable_root

        children = sorted(list(path
                               for path in root.iterdir()
                               if criteria(path)),
                          key=lambda s: str(s).lower())
        count = 1
        for path in children:
            is_last = count == len(children)
            if path.is_dir():
                yield from cls.make_tree(path,
                                         parent=displayable_root,
                                         child_to_highlight=child_to_highlight,
                                         is_last=is_last,
                                         criteria=criteria)
            else:
                yield cls(path, child_to_highlight, displayable_root, is_last)
            count += 1

    @classmethod
    def _default_criteria(cls, path):
        return True

    @property
    def displayname(self):
        if self.path.is_dir():
            return self.path.name + '/'
        if str(self.path) == self.child_to_highlight:
            return bcolors.OKGREEN + self.path.name + bcolors.ENDC
        return self.path.name

    def displayable(self):
        if self.parent is None:
            return self.displayname

        _filename_prefix = (self.display_filename_prefix_last
                            if self.is_last
                            else self.display_filename_prefix_middle)

        parts = ['{!s} {!s}'.format(_filename_prefix,
                                    self.displayname)]

        parent = self.parent
        while parent and parent.parent is not None:
            parts.append(self.display_parent_prefix_middle
                         if parent.is_last
                         else self.display_parent_prefix_last)
            parent = parent.parent

        return ''.join(reversed(parts))

class StateMachine:

    directories_to_ignore = []

    def __init__(self, files):
        self.files = files
        self.current_file = files[0]
        self.actions = {
                "d": self.delete_file,
                "D": self.delete_file_directory,
                "s": self.skip,
                "S": self.skip_directory,
                "?": self.print_help,
        }


    def transition(self):
        if not os.path.exists(self.current_file.path):
            # We have deleted this file by deleting it's directory
            self.advance()
        if self.current_file.directory in self.directories_to_ignore:
            # We have chosen to skip this directory
            self.advance()

        choice = self.prompt()

        if choice in self.actions:
            self.actions[choice]()
        else:
            return self.transition()

    def delete_file(self):
        self.current_file.delete_file()
        self.advance()

    def delete_file_directory(self):
        self.current_file.delete_file_directory()
        self.advance()

    def skip(self):
        self.advance()

    def skip_directory(self):
        self.directories_to_ignore.append(self.current_file.directory)
        self.advance()

    def advance(self):
        current_file_index = self.files.index(self.current_file)
        next_file_index = current_file_index + 1

        if next_file_index >= len(self.files):
            return
        else:
            self.current_file = self.files[next_file_index]
            return self.transition()

    def print_help(self):
        print()
        print("Choose from one of these options: ")
        print("  d  delete the file")
        print("  D  delete the directory which contains the file")
        print("  s  skip this file and go on to the next one")
        print("  S  skip this directory and go on to the next one")
        print("  ?  print this help menu")
        print()
        return self.transition()

    def prompt(self):
        self.current_file.print_as_tree()
        print()
        sys.stdout.write("Please choose an option: d,D,s,S,? ")
        return input()

class File:

    files = []

    @classmethod
    def files_by_size(klass):
        return sorted(klass.files, key=lambda x: x.size_in_bytes)

    @classmethod
    def files_by_age(klass):
        return sorted(klass.files, key=lambda x: x.age_in_days, reverse=True)

    def __init__(self, path, size_in_bytes, age_in_days):
        self.size_in_bytes = int(size_in_bytes)
        self.size_human_readable = self.convert_to_human_readable_size(size_in_bytes)
        self.path = path
        self.directory = self.determine_directory()
        self.age_in_days = age_in_days
        self.age_human_readable = "{} days".format(age_in_days)
        self.files.append(self)
        
    def determine_directory(self):
        return os.path.dirname(self.path)

    def convert_to_human_readable_size(self, size_in_bytes):
        if size_in_bytes == 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_in_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_in_bytes / p, 2)
        return "{} {}".format(s, size_name[i])

    def to_dict(self):
        return {
            "path": self.path,
            "directory": self.directory,
            "size": self.size_human_readable,
            "age": self.age_human_readable,
        }

    def __repr__(self):
        return json.dumps(self.to_dict(), indent=4)

    def print_as_tree(self):
        print("Absolute path: {}".format(self.path))
        paths = DisplayablePath.make_tree(Path(self.directory), self.path)
        for path in paths:
            print(path.displayable())

    def delete_file(self):
        os.remove(self.path)
        # TODO: If this would leave an empty directory, delete the directory

    def delete_file_directory(self):
        shutil.rmtree(self.directory)


def main():
     
    ensure_user_is_root()

    directory = sys.argv[1]
    order_by = sys.argv[2]

    for path in [os.path.abspath(p) for p in glob.glob(directory + "/**/*", recursive=True)]:
        if os.path.isdir(path):
            continue

        size = os.path.getsize(path)
        ctime = datetime.fromtimestamp(os.stat(path).st_ctime)
        age = datetime.now() - ctime
        
        File(path, size, age.days)

    if order_by == "age":
        files = File.files_by_age()
    elif order_by == "size":
        files = File.files_by_size()

    return StateMachine(files).transition()

if len(sys.argv) < 3:
    print_help()
    sys.exit(1)
else: 
    main()
