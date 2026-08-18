# Lecciones Aprendidas — Systemd Timers

## 1. Por qué cron falla en tareas de complejidad media/alta

Cron tiene cuatro debilidades que systemd timers resuelve de forma declarativa:

| Debilidad de cron | Solución en systemd |
|-------------------|---------------------|
| Fallos silenciosos (solo con `>> log 2>&1` manual por script) | journald captura stdout+stderr nativamente; un fallo deja la unidad en estado `failed` |
| Sin log de serie | `journalctl --user -u <unidad>` centralizado |
| Sin dependencias | `After=`/`Wants=` (`network-online.target`, montajes, etc.) |
| Tarea perdida si la máquina estaba apagada a la hora | `Persistent=true` ejecuta al encender |

## 2. `Persistent=true` solo recupera LA ÚLTIMA corrida perdida

Si la máquina estuvo apagada varios días, `Persistent=true` dispara UNA sola corrida de catch-up (la más reciente), no todas las acumuladas. Ideal para tareas idempotentes (reindexar, rebuild). Para tareas donde "cada corrida importa", no es suficiente.

## 3. Linger obligatorio para unidades de usuario

Sin `loginctl enable-linger <usuario>`, los timers de usuario solo corren mientras el usuario tiene una sesión iniciada. En un servidor headless, verificar:

```bash
loginctl show-user <usuario> | grep Linger   # debe decir Linger=yes
```

## 4. `enable --now` vs `start`

`systemctl --user start <tarea>.timer` solo activa el timer para la sesión actual y se pierde al reiniciar. `enable --now` lo registra en `timers.target` y sobrevive a reinicios.

## 5. `daemon-reload` tras editar

systemd mantiene en memoria la config vieja. Tras editar cualquier `.service`/`.timer`, ejecutar `systemctl --user daemon-reload`, o seguirá usando la versión anterior.

## 6. `Type=oneshot` bloquea `start`

`systemctl start` de un servicio oneshot no retorna hasta que el `ExecStart` termina. Si el script reintenta mucho, lanzar con `--no-block` o con timeout generoso.

## 7. Rutas absolutas

systemd no usa el PATH de la shell. Usar rutas absolutas en `ExecStart` y dentro de los scripts. Si el script usa `#!/usr/bin/env python3`, asegurar `/usr/bin` en el PATH (o definir `Environment=PATH=...`).

## 8. Migración atómica (evitar doble ejecución)

Quitar la línea del crontab EN EL MISMO paso en que se activa el timer. Si ambos quedan activos, la tarea corre dos veces. Backup del crontab antes: `crontab -l > backup.bak`.

## 9. Dependencia con host remoto (no nativa)

systemd no espera a un host remoto. `After=network-online.target` solo cubre la red local. Para un script que hace `scp`/`ssh` contra un servidor que se apaga de noche, usar un wrapper con reintento acotado (ver `migracion-cron.md`) o `Restart=on-failure` + `RestartSec`.

## 10. Guarda anti-doble-ejecución en el wrapper

Para tareas periódicas idempotentes, un wrapper con `flock` (serializar) + "skip si ya corrió hoy" evita doble ejecución cuando el timer y una corrida manual coinciden.
