"""Собрать необходимые шрифты для исходных PSD CIS Apex из ZIP-архива.

Запуск в PyCharm: Run -> collect_photoshop_fonts.py, затем выбрать ZIP.
Или в терминале: python collect_photoshop_fonts.py "ПУТЬ_К_АРХИВУ.zip"

Скрипт только извлекает файлы. Он НЕ устанавливает шрифты в Windows.
"""

import os
import shutil
import sys
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, BadZipFile

ROOT = Path(__file__).resolve().parent
DESTINATION = ROOT / "assets" / "fonts" / "photoshop_install"

# Названия сверены с содержимым архива «Шрифты и градиенты.zip».
FONT_FILES = {
    "Druk-Medium-Trial.otf": "Таблица: большой заголовок (DrukTrial-Medium)",
    "steelfish rg.ttf": "MVP: большой MATCH 5 (SteelfishRg-Regular)",
    "InterTight-Medium.ttf": "Команды и ники (InterTight-Medium)",
    "InterTight-Regular.ttf": "MVP: верхняя строка (InterTight-Regular)",
    "Inter_24pt-Medium.ttf": "Кандидат на замену Inter-Medium",
    "Inter_24pt-SemiBold.ttf": "Кандидат на замену Inter-SemiBold",
    "Inter-VariableFont_opsz,wght.ttf": "Дополнительный вариант семейства Inter",
}


def choose_archive():
    if len(sys.argv) > 1:
        return Path(sys.argv[1].strip('"'))

    from tkinter import Tk, filedialog

    root = Tk()
    root.withdraw()
    try:
        path = filedialog.askopenfilename(
            title="Выбери архив «Шрифты и градиенты.zip»",
            filetypes=[("ZIP-архивы", "*.zip")],
        )
    finally:
        root.destroy()
    return Path(path) if path else None


def main():
    archive = choose_archive()
    if archive is None:
        print("Архив не выбран.")
        return
    if not archive.is_file():
        print(f"Файл не найден: {archive}")
        return

    try:
        with ZipFile(archive) as zipped:
            # Ищем по имени файла, независимо от вложенных папок в архиве.
            by_name = {}
            for member in zipped.infolist():
                if member.is_dir():
                    continue
                filename = PurePosixPath(member.filename).name.casefold()
                by_name.setdefault(filename, member)

            DESTINATION.mkdir(parents=True, exist_ok=True)
            found = 0
            missing = []

            for filename, description in FONT_FILES.items():
                member = by_name.get(filename.casefold())
                if member is None:
                    missing.append(filename)
                    print(f"НЕ НАЙДЕН: {filename}")
                    continue

                # Записываем в заранее известное имя файла, а не по пути из ZIP.
                output = DESTINATION / filename
                with zipped.open(member) as source, output.open("wb") as target:
                    shutil.copyfileobj(source, target)
                found += 1
                print(f"OK: {filename} — {description}")
    except BadZipFile:
        print("Ошибка: выбранный файл не является корректным ZIP-архивом.")
        return

    print(f"\nГотово: найдено {found} из {len(FONT_FILES)} шрифтов.")
    if missing:
        print("Отсутствуют:", ", ".join(missing))
    print(f"Папка: {DESTINATION}")
    print("\nДалее: выдели .ttf и .otf в этой папке -> правая кнопка мыши -> Установить")
    print("(или «Показать дополнительные параметры» -> «Установить»).")
    print("После установки полностью перезапусти Photoshop.")
    print("\nВНИМАНИЕ: версии Inter 24pt имеют другие внутренние имена, чем")
    print("Inter-Medium / Inter-SemiBold в старом PSD. Если Photoshop всё ещё")
    print("предлагает замену шрифта, выбери подходящий Inter вручную и сохрани шаблон.")
    print("Druk Trial — ознакомительная версия: проверь лицензию перед публикацией.")

    if os.name == "nt":
        try:
            os.startfile(str(DESTINATION))
        except OSError:
            pass


if __name__ == "__main__":
    main()
