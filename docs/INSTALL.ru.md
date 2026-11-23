<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Установка 0.1.1 с GitHub без AUR

Релиз: <https://github.com/1sSay/asus-zenbook-fan-driver/releases/tag/v0.1.1>.
Пакет можно собрать и установить через pacman без аккаунта AUR и AUR helper.
Ниже описан проверенный путь для **Arch Linux x86_64 с systemd**.

## Совместимость и статус

Это экспериментальный userspace-драйвер для ASUS Zenbook UX425QA/UM425QA,
HealthyTable **8**, ровно двух вентиляторов. Владелец называет ноутбук UM425Q,
но это не расширяет список поддерживаемых устройств. Проверьте:

```sh
uname -m
cat /sys/class/dmi/id/product_name
```

Архитектура должна быть `x86_64`, DMI — строго `Zenbook UX425QA_UM425QA`
или `ZenBook UX425QA_UM425QA`. Версию контроллера и число вентиляторов проверяет
worker при обращении к EC. Другие модели отклоняются; обхода проверок нет.

Чистая сборка Arch, тесты с симулятором EC и установка во временный каталог
проверены. Приёмка реального оборудования, GUI, сна/пробуждения и обновления/
удаления работающей службы отложена. Профили и восстановление этой версии
не заявлены аппаратно подтверждёнными. Сборка и установка не запускают службу;
её последующий запуск уже обращается к оборудованию. Не запускайте одновременно
другие программы прямого доступа к EC.

## 1. Подготовить инструменты

```sh
sudo pacman -Syu --needed base-devel python curl
```

Runtime-зависимости пакета: `glibc`, `python`, `systemd`. `makepkg --syncdeps`
установит отсутствующие зависимости через pacman. Саму сборку запускайте
**обычным пользователем**, не через sudo.

## 2. Скачать и проверить рецепт сборки

Создайте отдельный каталог и скачайте вложения релиза:

```sh
mkdir asus-zenbook-fan-driver-0.1.1-install
cd asus-zenbook-fan-driver-0.1.1-install
release=https://github.com/1sSay/asus-zenbook-fan-driver/releases/download/v0.1.1
curl --fail --location --remote-name "$release/asus-zenbook-fan-driver-0.1.1-arch-build.tar.gz"
curl --fail --location --remote-name "$release/SHA256SUMS"
sha256sum --check --ignore-missing SHA256SUMS
```

Убедитесь, что для `asus-zenbook-fan-driver-0.1.1-arch-build.tar.gz` получено
`OK`. Отсутствующие исходник и руководство из общего списка пропускаются.
При несовпадении суммы остановитесь и скачайте файлы заново из этого релиза.

```sh
tar -xzf asus-zenbook-fan-driver-0.1.1-arch-build.tar.gz
cd asus-zenbook-fan-driver-0.1.1-arch-build
less PKGBUILD
```

Архив содержит только `PKGBUILD`, `.SRCINFO` и лицензию упаковки `LICENSE`.
Просмотрите PKGBUILD: makepkg выполняет этот сценарий от вашего имени.
Исходник программы он скачает сам по HTTPS из того же GitHub-релиза и проверит
его SHA256:

```text
b0992c43001a001699f4f70d925b8d03e7ec29a14faafc00795675091e02a3eb
```

Используется вложение `asus-zenbook-fan-driver-0.1.1.tar.gz`, а не автоматически
созданный GitHub архив «Source code»: у них разный байтовый состав.

## 3. Собрать и установить пакет

```sh
makepkg --syncdeps --check
sudo pacman -U ./asus-zenbook-fan-driver-0.1.1-1-x86_64.pkg.tar.zst
```

Имя выше соответствует стандартным настройкам Arch. Если вы меняли `PKGDEST`
или формат пакетов в makepkg.conf, найдите получившийся файл через
`makepkg --packagelist` и установите основной пакет из этого списка.
Автоматически создаваемый пакет `-debug` для работы не требуется.

Проверки сборки используют фиктивный EC: сообщения о full duty, восстановлении
и оборотах относятся к симулятору. Сборка не запускает реальный maximum test,
не обращается к EC и не включает службу. Файлы устанавливаются под `/usr` и
учитываются pacman; `sudo make install` для этого пути не нужен.

## 4. Проверить установку до запуска

```sh
asus-zenbook-fan-driver --version
asus-zenbook-fan-driver doctor
```

Ожидаемая версия — `0.1.1`. До запуска службы doctor может завершиться кодом 1
из-за неактивной службы и отсутствующей телеметрии: это ожидаемо. Код 2 означает
неполную диагностику, код 0 — успешные обязательные проверки на момент вызова.
Doctor не запускает worker и не обращается к EC; совпадение DMI не доказывает
версию контроллера или аппаратную безопасность.

## 5. Явно запустить службу

Если установлен старый прототип `asus-fan-rpm.service`, сначала сохраните его
файлы и остановите/отключите старую службу. Миграция описана в README.
Продолжайте на поддерживаемом ноутбуке, когда готовы к доступу службы к EC:

```sh
sudo systemctl daemon-reload
sudo systemctl start asus-zenbook-fan-driver.service
systemctl status asus-zenbook-fan-driver.service --no-pager
asus-zenbook-fan-driver status
asus-zenbook-fan-driver doctor
```

В статусе должны появиться **Fan 1 / Fan 2**. `0 RPM` допустим; `null`, старые
данные и ошибки восстановления требуют проверки. Обычный мониторинг не пишет
mode/PWM; при оставшейся recovery lease worker сначала пытается восстановить
автоматический режим. Это не проверка с максимальными оборотами.

Если результат устраивает, включите автозапуск:

```sh
sudo systemctl enable asus-zenbook-fan-driver.service
```

При проблемах смотрите журнал:

```sh
journalctl -u asus-zenbook-fan-driver.service -b --no-pager -n 80
asus-zenbook-fan-driver doctor --json
```

Отказ из-за модели/контроллера не обходите. Ошибка raw I/O может быть связана
с kernel lockdown или недоступным CAP_SYS_RAWIO; fallback через `/dev/mem` нет.

## 6. Профили и возврат к прошивке

Профиль включается отдельной командой с правами администратора:

```sh
sudo asus-zenbook-fan-driver balanced
asus-zenbook-fan-driver status
```

Также доступны `quiet` и `performance`. Это фиксированные температурные кривые,
а не произвольная установка PWM. Для них нужен датчик AMD `k10temp`. На 95 °C
или при недоступном датчике предусмотрен возврат к управлению прошивкой.
Кривые остаются экспериментальными; подробно они описаны в README.

Для возврата к автоматическому управлению прошивки при работающей службе:

```sh
sudo asus-zenbook-fan-driver restore-auto
```

Если восстановление не подтверждено, изучите журнал; если повторное
`restore-auto` не помогло, перезагрузите ноутбук. Не считайте нулевой PWM
автоматическим режимом. Команда `test-max` не нужна для установки и не входит
в эту инструкцию проверки.

## 7. Необязательный графический интерфейс

```sh
sudo pacman -Syu --needed tk polkit
```

В графической сессии должен работать polkit authentication agent вашей среды.
Откройте **ASUS Zenbook fans** в меню приложений или выполните обычным
пользователем:

```sh
python3 -I /usr/lib/asus-zenbook-fan-driver/gui.py
```

GUI показывает телеметрию, а для изменения профиля запрашивает отдельную
администраторскую авторизацию. Запускать GUI через sudo не нужно. Если agent
отсутствует или авторизация отменена, профиль не переключится. Подробности:
<https://github.com/1sSay/asus-zenbook-fan-driver/blob/main/docs/DESKTOP.md>.

## 8. Обновление и удаление

Перед обновлением или удалением при работающей службе выполните
`sudo asus-zenbook-fan-driver restore-auto` и убедитесь, что восстановление
подтверждено. Затем остановите службу. При ошибке восстановления сначала
разберите её или перезагрузитесь, а не удаляйте работающий контроллер.

Для обновления соберите пакет нового релиза по его инструкции и выполните:

```sh
sudo systemctl stop asus-zenbook-fan-driver.service
sudo pacman -U /путь/к/новому-пакету.pkg.tar.zst
sudo systemctl daemon-reload
sudo systemctl start asus-zenbook-fan-driver.service
asus-zenbook-fan-driver doctor
```

Для удаления:

```sh
sudo systemctl disable --now asus-zenbook-fan-driver.service
sudo pacman -R asus-zenbook-fan-driver
sudo systemctl daemon-reload
```

Оставшиеся runtime-файлы находятся под `/run` и не являются установленными
бинарниками. Не удаляйте recovery lease для сокрытия ошибки восстановления.

## Другие дистрибутивы и лицензия

Этот путь установки и пакет проверены для Arch Linux x86_64. Для других
дистрибутивов готовый pacman-пакет не предназначен; общие команды сборки и
staged install приведены в README, но установка там отдельно не проверена.

Программа — GPL-3.0-or-later с сохранёнными сторонними уведомлениями;
упаковка — 0BSD. Версия, исходник и контрольные суммы доступны в GitHub-релизе.
Справка по инструментам: [makepkg](https://man.archlinux.org/man/makepkg.8.en),
[pacman](https://man.archlinux.org/man/pacman.8.en).
