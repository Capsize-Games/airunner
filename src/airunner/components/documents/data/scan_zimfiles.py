import os
import json

from airunner.components.documents.data.document_records import (
    create_zim_file,
    delete_zim_file,
    find_zim_file_by_path,
    list_zim_files,
    update_zim_file,
)


def scan_zimfiles(zim_dir: str) -> bool:
    """Scan the zim_dir for .zim files, update ZimFile DB, and remove missing ones.
    Returns True if any changes were made."""
    zim_dir = os.path.expanduser(zim_dir)
    if not os.path.exists(zim_dir):
        os.makedirs(zim_dir, exist_ok=True)
    found = set()
    changed = False
    for fname in os.listdir(zim_dir):
        if not fname.lower().endswith(".zim"):
            continue
        fpath = os.path.join(zim_dir, fname)
        found.add(fpath)
        meta_path = fpath + ".json"
        meta = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as mf:
                    meta = json.load(mf)
            except Exception:
                meta = {}
        item = find_zim_file_by_path(fpath)
        if not item:
            create_zim_file(
                {
                    "path": fpath,
                    "name": fname,
                    "title": meta.get("title"),
                    "summary": meta.get("summary"),
                    "updated": meta.get("updated"),
                    "size": os.path.getsize(fpath),
                }
            )
            changed = True
        else:
            # Update metadata if changed
            updates = {}
            for field in ["title", "summary", "updated"]:
                val = meta.get(field)
                if getattr(item, field) != val:
                    updates[field] = val
            size = os.path.getsize(fpath)
            if item.size != size:
                updates["size"] = size
            if updates:
                update_zim_file(item.id, updates)
                changed = True
    # Remove missing
    for item in list_zim_files():
        if item.path not in found:
            delete_zim_file(item.id)
            changed = True
    return changed
