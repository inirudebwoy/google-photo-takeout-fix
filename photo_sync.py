import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Callable, Dict, Iterator, List


conn = sqlite3.connect("photo_sync.db")


DONT_IMPORT_MARKER_EXT = ".dont_import"

META_EXT = (".json",)
SKIPPED_EXT = META_EXT
SKIPPED_FILES = ".DS_Store"


def bracket_name(path: Path) -> float:
    p, ext = os.path.splitext(path)
    # remove (1)
    filepath = p[:-3]
    index_ = p[-3:]
    # add .jpg(1).json
    print("Path with (1): ", filepath)
    with open(filepath + f"{ext}{index_}.json") as meta_file:
        meta: Dict = json.load(meta_file)

    return meta["photoTakenTime"]["timestamp"]


def regular_name_json(path: Path) -> float:
    print("Path without (1): ", path)
    json_path = Path(str(path) + ".json")
    with json_path.open() as meta_file:
        meta: Dict = json.load(meta_file)

    return meta["photoTakenTime"]["timestamp"]


def only_json(path: Path) -> float:
    print("Trying meta file with out .jpg extension.")
    # some files do not have .jpg in file name but only .json
    file_no_ext, _ = os.path.splitext(path)
    with open(Path(file_no_ext).with_suffix(".json")) as meta_file:
        meta: Dict = json.load(meta_file)

    return meta["photoTakenTime"]["timestamp"]


def only_json_cut(path: Path) -> float:
    print("Trying meta file with out .jpg extension.")
    # some files do not have .jpg in file name but only .json
    file_no_ext, _ = os.path.splitext(path)
    with open(Path(file_no_ext[:-1]).with_suffix(".json")) as meta_file:
        meta: Dict = json.load(meta_file)

    return meta["photoTakenTime"]["timestamp"]


def find_timestamp(path: Path) -> float:

    finders: List[Callable] = [
        bracket_name,
        regular_name_json,
        only_json,
        only_json_cut,
    ]
    for f in finders:
        try:
            return f(path)
        except FileNotFoundError:
            continue

    return 0


def photos(path: Path) -> Iterator[Path]:
    for p in path.glob("**/*"):
        if p.is_dir():
            continue

        _, ext = os.path.splitext(p)
        if ext in SKIPPED_EXT or p.name in SKIPPED_FILES:
            # this is obvious, we only want media files
            continue

        if DONT_IMPORT_MARKER_EXT in p.name:
            # TODO: count those
            continue

        if "edited" in p.name:
            # edited versions of images, most probably in Google Photos
            # can be skipped as those are duplicates

            destination_path = str(p) + DONT_IMPORT_MARKER_EXT
            os.rename(p, destination_path)
            print("This file will not be imported: ", destination_path)
            continue

        yield p


def scan(path: Path, db_conn: sqlite3.Connection):
    for photo in photos(path):
        timestamp_ = find_timestamp(photo)

        print("Photo taken timestamp, ", timestamp_)
        db_conn.execute(
            """INSERT INTO photos 
            VALUES (:abs_path, :parent_path, :file_name, :creation_date)
            ON CONFLICT(abs_path) DO NOTHING""",
            {
                "abs_path": str(photo.absolute()),
                "parent_path": str(photo.parent),
                "file_name": photo.name,
                "creation_date": timestamp_,
            },
        )
        db_conn.commit()


def estimate_misses(db_conn: sqlite3.Connection):
    c = db_conn.cursor()
    c.execute("SELECT * FROM photos WHERE creation_date = 0")
    # TODO: LEVEL HARD
    # I believe this could be done with cursor window
    # fetch all group having same parent_path
    # update all with 0 with group average
    for row in c.fetchall():
        print("Calculating timestamp for abs_path: ", row[0])
        avg_creation_date = c.execute(
            "SELECT AVG(creation_date) FROM photos WHERE creation_date != 0 AND parent_path = ?",
            (row[1],),
        ).fetchone()
        print("Estimated timestamp is ", avg_creation_date)
        c.execute(
            "UPDATE photos SET creation_date = ? WHERE abs_path = ?",
            (int(avg_creation_date[0]), row[0]),
        )

    db_conn.commit()


def apply_timestamps(path: Path, db_conn: sqlite3.Connection):
    c = db_conn.cursor()
    c.execute("SELECT * FROM photos WHERE creation_date != 0")
    for row in c.fetchall():
        os.utime(row[0], times=(row[3], row[3]))


def start(path: Path):
    print("Start scanning path: ", path)
    scan(path, conn)
    print("Estimate misses")
    estimate_misses(conn)
    print("Apply timestamps")
    apply_timestamps(path, conn)

    c = conn.cursor()

    print("Scanning report")
    print(
        "Scanned files count: %s", c.execute("SELECT COUNT(*) FROM photos").fetchone()
    )
    print(
        "Files without timestamp: %s",
        conn.execute("SELECT COUNT(*) FROM photos WHERE creation_date = 0").fetchone(),
    )

    conn.close()


if __name__ == "__main__":
    try:
        source_dir = Path(sys.argv[1])
    except IndexError:
        raise SystemExit(f"Usage: {sys.argv[0]} <path_to_pictures>")

    try:
        conn.execute(
            """CREATE TABLE photos
        (abs_path text PRIMARY KEY, parent_path text, file_name text, creation_date int)"""
        )
    except sqlite3.OperationalError:
        # table most likely exists
        pass

    conn.commit()

    start(source_dir)