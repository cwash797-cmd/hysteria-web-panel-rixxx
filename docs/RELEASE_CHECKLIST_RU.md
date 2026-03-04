# Release Checklist (RU) - Hysteria Web Panel v1.0.0

Этот чек-лист пройти перед публикацией на GitHub.

## 1. Функциональные проверки

- [ ] Вход в панель работает.
- [ ] `GET /health` возвращает `{"ok":true}`.
- [ ] Создание пользователя работает.
- [ ] Удаление пользователя работает.
- [ ] `Link / YAML / QR` работают из web UI.
- [ ] Кнопка `Restart HY2` работает.
- [ ] Управление сроком (`+30d`, `-30d`, `Бессрочно`) работает.
- [ ] Просроченный пользователь переходит в inactive и отключается.

## 2. Проверка Hysteria

- [ ] `systemctl status hysteria-server --no-pager` -> active.
- [ ] `ss -lunp | grep 443` показывает запущенный hysteria.
- [ ] Клиент Happ Plus подключается по `hy2://`.
- [ ] Домен/SNI в ссылке совпадает с `acme.domains`.

## 3. Проверка панели (backend)

- [ ] `systemctl status hwp --no-pager` -> active.
- [ ] `journalctl -u hwp -n 100 --no-pager` без критических ошибок.
- [ ] `scripts/smoke_test.sh` проходит до `Smoke test passed`.

## 4. Проверка внешнего доступа панели

- [ ] `cloudflared` сервис активен.
- [ ] DNS поддомена панели резолвится в Cloudflare IP.
- [ ] `curl -Iv https://<panel-domain>` отвечает корректно.
- [ ] Панель открывается из внешней сети (не только локально/SSH туннель).

## 5. Безопасность перед релизом

- [ ] Сменены все тестовые пароли и API ключи.
- [ ] `HWP_ADMIN_PASSWORD` сильный и уникальный.
- [ ] `HWP_API_KEYS` сильные и уникальные.
- [ ] В `.env.example` нет реальных секретов.
- [ ] В репозиторий не попал `.env`.
- [ ] Проверено, что нет токенов/ключей в README и коммитах.

## 6. Документация

- [ ] `README.md` актуален.
- [ ] `README.ru.md` актуален.
- [ ] `docs/DEPLOYMENT.md` актуален.
- [ ] `docs/SECURITY.md` актуален.
- [ ] Добавлен этот файл `docs/RELEASE_CHECKLIST_RU.md`.

## 7. GitHub публикация

- [ ] Проставлен `v1.0.0` в release notes.
- [ ] Загружен changelog (что реализовано).
- [ ] Добавлены примеры команд установки.
- [ ] Приложены известные ограничения (single-node по умолчанию).

## 8. Пост-релиз

- [ ] Записан issue-лист на v1.1:
  - Multi-node режим
  - RBAC/роли
  - Webhook retries + idempotency
  - 2FA для админа
