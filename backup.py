
import hashlib
import json
import shutil
import tarfile
import time

from datetime import datetime
from pathlib import Path

SOURCE = Path("company_data")
BACKUP_DIR = Path("backups")
KEEP_LAST = 8


# Вычисление SHA-256
def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)

    return h.hexdigest()


# Создание списка контрольных сумм файлов
def make_manifest(folder):
    return {
        str(p.relative_to(folder)): sha256(p)
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }


# Создание резервной копии
def create_backup():
    BACKUP_DIR.mkdir(exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive = BACKUP_DIR / f"backup_{stamp}.tar.gz"

    with tarfile.open(archive, "w:gz") as tar:
        tar.add(SOURCE, arcname=SOURCE.name)

    manifest = {
        "created": stamp,
        "archive_sha256": sha256(archive),
        "files": make_manifest(SOURCE)
    }

    json_path = archive.with_suffix("").with_suffix(".json")

    json_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"[OK] Создан архив: {archive.name}")
    print(f"[OK] Количество файлов: {len(manifest['files'])}")
    print(f"[OK] Размер: {archive.stat().st_size / 1024:.1f} КБ")

    return archive


# Удаление старых резервных копий
def rotate():
    archives = sorted(BACKUP_DIR.glob("backup_*.tar.gz"))

    for old in archives[:-KEEP_LAST]:
        old.unlink()

        json_path = old.with_suffix("").with_suffix(".json")
        json_path.unlink(missing_ok=True)

        print(f"[ROTATE] Удалена старая копия: {old.name}")


# Проверка восстановления и целостности
def verify_restore(archive):
    json_path = archive.with_suffix("").with_suffix(".json")

    manifest = json.loads(
        json_path.read_text(encoding="utf-8")
    )

    if sha256(archive) != manifest["archive_sha256"]:
        print("[FAIL] Архив повреждён!")
        return False

    tmp = Path("restore_test")

    shutil.rmtree(tmp, ignore_errors=True)

    with tarfile.open(archive) as tar:
        tar.extractall(tmp, filter="data")

    restored = make_manifest(tmp / SOURCE.name)

    shutil.rmtree(tmp)

    expected = manifest["files"]

    missing = set(expected) - set(restored)
    extra = set(restored) - set(expected)

    changed = {
        name for name in set(expected) & set(restored)
        if expected[name] != restored[name]
    }

    print("\n--- ОТЧЁТ ПРОВЕРКИ ---")

    print("Отсутствующие файлы:", missing)
    print("Лишние файлы:", extra)
    print("Изменённые файлы:", changed)

    if not missing and not extra and not changed:
        print("[OK] Восстановление проверено!")
        print(f"Совпадает файлов: {len(restored)}")
        return True

    print("[FAIL] Данные не совпадают!")
    return False


# Восстановление после инцидента
def restore(archive):
    start = time.perf_counter()

    if not archive.exists():
        print("[FAIL] Архив не найден!")
        return False

    if not verify_archive_hash(archive):
        print("[FAIL] Архив повреждён!")
        return False

    shutil.rmtree(SOURCE, ignore_errors=True)

    with tarfile.open(archive) as tar:
        tar.extractall(".", filter="data")

    elapsed = time.perf_counter() - start

    print("\n[OK] Данные восстановлены!")
    print(f"Время восстановления: {elapsed:.3f} секунд")

    return True


# Проверка контрольной суммы архива
def verify_archive_hash(archive):
    json_path = archive.with_suffix("").with_suffix(".json")

    manifest = json.loads(
        json_path.read_text(encoding="utf-8")
    )

    return sha256(archive) == manifest["archive_sha256"]


if __name__ == "__main__":
    archives = sorted(BACKUP_DIR.glob("backup_*.tar.gz"))

    latest = archives[-1]

    print("Выбрана копия:", latest.name)

    restore(latest)
