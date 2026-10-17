# Apex Stats Pipeline

Это **предварительная сборка** удобного запуска и адаптера Apex Legends Status.
Рабочие `main.py`, `stats.py`, `export_photoshop.py`, `player_names.py` и
`photoshop/fill_from_json.jsx` сохранены по смыслу, но содержат изменения.

## Установка

1. Сначала сделайте Git-коммит текущей рабочей Photoshop-версии.
2. Скопируйте содержимое этой папки в корень `apex-stats-pipeline` с заменой одноимённых файлов.
3. Для Apex Legends Status установите зависимости:
   `python -m pip install -r requirements.txt` (или `.venv\Scripts\python.exe -m pip install -r requirements.txt`).
4. Запускайте двойным кликом `ЗАПУСК.bat`. Для запуска из PyCharm подходит `launcher.py`.
5. Выберите Eternal Esports или ALS, тип публикации и номер матча.
6. Программа сохранит JSON и попробует передать его в Photoshop автоматически через Windows COM.
   **Этот механизм ещё не был опробован на Photoshop 26.9.**
7. При неудаче Photoshop всё равно можно запустить вручную: `Файл → Сценарии → Обзор`
   и выбрать `photoshop/fill_from_json.jsx`, затем JSON в `output/photoshop`.

## ALS: ссылка на конкретный этап

Используйте страницу **конкретной серии** с `score-matrix_table`, например
`https://apexlegendsstatus.com/algs/Y6-Split1/ALGS-Playoffs/Global/Finals/Finals`,
а **не** `Overview`, где смешаны этапы турнира.

Парсер делает две независимые вещи:
- читает командные места и киллы из `score-matrix_table` - для турнирной таблицы;
- открывает каждый `View game stats` и читает `players-stats`, включая убийства/урон, а также
  пытается получить легенды из `showLobbyLayout` на странице серии - для MVP.

Проверка на реальных страницах **конкретного LAN турнира** ещё обязательна. Нельзя
публиковать MVP без проверки легенд и соответствия игрового ника.
Если `players-stats` отсутствует или легенда не установлена, генерация MVP должна
завершиться ошибкой, не подставляя вымышленные цифры.

## Два источника, одни расчёты

`main.py --source eternal` - прежний локальный Eternal Esports JSON.

`main.py --source als --als-url <stage-url> --job table` - таблица ALS.

`main.py --source als --als-url <stage-url> --job mvp --match 3` - MVP ALS, после проверки персональных данных.

Фотография и логотипы на MVP всегда добавляются вручную в Photoshop.

## Новые шаблоны

Каждый тип поста должен иметь свой экспортер и обработчик PSD. Новый PSD не должен
менять расчёты `stats.py` или источники данных.

## Ограничения

Сейчас нет автоматической загрузки новых матчей по расписанию и нет полной проверки
парсинга ALS на живой странице. Windows Photoshop COM также нужно проверить на реальном ПК.
При наличии штрафов/бонусов очки в `score-matrix_table` могут отличаться от ALGS-суммы;
программа выдаёт предупреждение.
