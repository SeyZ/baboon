import os


def get_ordered_files(folder, excludes=[]):

    f_items = []
    for path, dirs, files in os.walk(folder):
        for f in files:
            rel_path = os.path.join(os.path.relpath(path, folder), f)
            if f not in excludes:
                f_items.append(rel_path)

    f_items.sort()
    return f_items


def reset_file_tarinfo(tarinfo):

    tarinfo.uid = tarinfo.gid = tarinfo.mtime = 0
    tarinfo.uname = tarinfo.gname = 'baboon'
    tarinfo.mode = 0755 if tarinfo.isdir() else 0644
    tarinfo.mtime = 0
    return tarinfo
