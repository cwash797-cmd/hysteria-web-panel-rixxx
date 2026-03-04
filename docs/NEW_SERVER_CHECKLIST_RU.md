# Новый сервер: что менять и где (полный чек-лист)

Этот файл для ситуации, когда у вас новый VPS с новым IP и вы хотите поднять панель с нуля.

## 1) Что подготовить до установки

- Новый домен для Hysteria2, например: `edge.newdomain.xyz`
- (Опционально) поддомен панели, например: `panel.newdomain.xyz`
- DNS записи:
  - `A edge.newdomain.xyz -> NEW_SERVER_IP` (обычно DNS only)
- для панели рекомендуется Cloudflare Tunnel (`CNAME panel -> <tunnel-id>.cfargotunnel.com`)

## 2) Что меняется в Hysteria2 (на сервере)

В `/etc/hysteria/config.yaml`:

- `acme.domains` -> новый домен Hysteria (`edge.newdomain.xyz`)
- `acme.email` -> валидный email ASCII
- `auth.userpass` -> ваши пользователи

Пример:

```yaml
listen: :443

acme:
  type: http
  domains:
    - edge.newdomain.xyz
  email: admin@example.com

auth:
  type: userpass
  userpass:
    Admin: 1d2eb9f239f5046a41a5cbd2a2cf51d0
```

## 3) Что меняется в панели (переменные окружения)

В `.env` панели:

- `HWP_PUBLIC_DOMAIN=edge.newdomain.xyz`
- `HWP_PUBLIC_PORT=443`
- `HWP_PUBLIC_SNI=edge.newdomain.xyz`
- `HWP_HYSTERIA_CONFIG_PATH=/etc/hysteria/config.yaml`
- `HWP_HYSTERIA_SERVICE_NAME=hysteria-server`
- `HWP_ADMIN_USER=admin`
- `HWP_ADMIN_PASSWORD=<strong_password>`
- `HWP_API_KEYS=<long_random_key>`

## 4) Одна команда установки панели

После публикации репозитория:

```bash
curl -fsSL https://raw.githubusercontent.com/cwash797-cmd/hysteria-web-panel-rixxx/main/scripts/install.sh | \
sudo REPO_URL="https://github.com/cwash797-cmd/hysteria-web-panel-rixxx.git" \
HWP_PUBLIC_DOMAIN="edge.newdomain.xyz" \
bash
```

По умолчанию панель работает на `127.0.0.1:8080`.
Для внешнего доступа используйте Cloudflare Tunnel.

## 5) Что проверить сразу после установки

```bash
systemctl status hysteria-server --no-pager
systemctl status hwp --no-pager
journalctl -u hwp -n 80 --no-pager
curl -s http://127.0.0.1:8080/health
```

## 6) Проверка функционала панели (вручную)

1. Открыть панель и войти.
2. Создать тестового пользователя.
3. Нажать `Link` и проверить `hy2://...`.
4. Скачать `YAML`.
5. Удалить тестового пользователя.

## 7) Где менять при переезде на новый IP в будущем

- DNS `A` записи домена(ов)
- `acme.domains` в Hysteria
- `HWP_PUBLIC_DOMAIN` / `HWP_PUBLIC_SNI` в панели
- (позже в Worker) `API_BASE` и, при необходимости, `PUBLIC_HOST`
