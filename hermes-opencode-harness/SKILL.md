---
name: hermes-opencode-harness
description: "SDD harness: Hermes + OpenCode workflow for spec-driven dev."
version: 1.0.0
author: Hermes Agent Community
license: MIT
---

# Hermes + OpenCode — SDD Harness

Patrón de integración entre Hermes Agent y OpenCode CLI para Spec-Driven Development. Hermes actúa como orquestador (intake + líder de ciclo), OpenCode ejecuta specs, implementación y revisión con subagentes especializados.

## Arquitectura

```
feature_list.json  →  specs/{NN}_{name}/  →  OpenCode subagentes  →  código
     ↑                      ↑                       ↑                   ↑
  Hermes               Humano + Hermes          OpenCode             Humano
  (intake)            (spec authoring)     (implement/review)      (pruebas)

Flujo: F0 → F1 → F2 → F3  (features SDD)
       B1 → B2 → B3 → B4  (bugs)
```

## Estructura del proyecto

```
<proyecto>/
├── opencode.json              ← Config de OpenCode: instrucciones, comandos, skills
├── harness/
│   ├── AGENTS.md              ← Punto de entrada para cualquier agente
│   ├── feature_list.json      ← Single source of truth
│   ├── VERSION                ← Semver del harness
│   ├── .session               ← open/closed (fusible de protección)
│   ├── .opencode/agents/      ← Subagentes: leader, spec-author, implementer...
│   ├── specs/{NN}_{name}/     ← requirements.md + design.md + tasks.md
│   ├── progress/              ← current.md, history.md, closures, bloqueos
│   ├── learnings/             ← Lecciones acumuladas por rol
│   └── docs/                  ← architecture, conventions, specs, sessions
```

## opencode.json — Comandos custom

```json
{
  "instructions": ["harness/AGENTS.md", "harness/docs/architecture.md"],
  "command": {
    "init": "Verifica el entorno antes de empezar",
    "next": "Lee feature_list.json, lanza la primera feature spec-reviewed con implementer",
    "new_feature": "Lanza intake-agent para guiar al humano en la definición de una feature",
    "close": "Cierre limpio: verificación → closure → feature_list.json → .session=closed"
  },
  "skills": { "paths": ["harness/.opencode/skills"] }
}
```

## feature_list.json — Single Source of Truth

```json
{
  "project": "<nombre>",
  "rules": {
    "one_feature_at_a_time": true,
    "require_approved_spec_to_implement": true,
    "valid_status": ["pending","defined","spec_ready","spec-reviewed",
                     "in_progress","testing","done","blocked","untriaged","triaged"],
    "sdd_required_when": "feature has sdd: true"
  },
  "features": []
}
```

### Feature entry

```json
{
  "id": 1,
  "name": "<snake_case_unique>",
  "title": "<Título legible>",
  "type": "feature",
  "description": "<1-2 párrafos>",
  "acceptance": ["<criterio 1>", "<criterio 2>"],
  "proposed_by": "<nombre>",
  "sdd": true,
  "status": "pending",
  "depends_on": [],
  "beneficiaries": "<personas beneficiadas>"
}
```

### Bug entry

```json
{
  "id": 2,
  "name": "<snake_case_unique>",
  "title": "<Título>",
  "type": "bug",
  "description": "<descripción del fallo>",
  "reproduction": ["<paso 1>", "<paso 2>"],
  "affected_feature_ids": [1],
  "status": "untriaged"
}
```

## Estados y flujo

```
FEATURES (sdd: true):
  pending → defined → spec_ready → spec-reviewed → in_progress → testing → done
               ↑         ↑              ↑               ↑            ↑
           ⏸Humano   spec-author   spec-validator   ⏸Humano     ⏸Humano
                          ↓                              ↓
                      blocked  ←─────────────────────────┘

BUGS (type: bug):
  untriaged → triaged → in_progress → testing → done
       ↑         ↑           ↑           ↑        ↑
    ⏸Humano   bug-fixer   reviewer   ⏸Humano  release-mgr
```

## Subagentes OpenCode

| Agente | Rol |
|---|---|
| **leader** | Orquesta el flujo, presenta puertas humanas |
| **spec-author** | Redacta requirements.md + design.md + tasks.md en EARS |
| **spec-validator** | Valida spec contra EARS, cierra gaps |
| **implementer** | Implementa código desde tasks.md |
| **reviewer** | Revisa código, trazabilidad, convenciones |
| **bug-fixer** | Diagnostica y corrige bugs |
| **intake-agent** | Guía al humano para registrar feature/bug |
| **release-manager** | Cierra features: changelog, version, sync |

## Intake Protocol

### Fase 0 — Descubrimiento (método socrático)

1. **¿Qué problema resuelve?** ¿Por qué es necesario ahora?
2. **¿Quién lo usará y en qué escenario?** Flujo de uso concreto.
3. **¿Cómo se hace hoy?** Papel, Excel, manual...
4. **¿Qué es lo que más duele del proceso actual?**
5. **¿Hay restricciones?** Tiempo, presupuesto, sistemas existentes.

### Fase 1 — Recolección estructurada

1. **Nombre** (snake_case único)
2. **Título** legible
3. **Descripción** (1-2 párrafos)
4. **Criterios de aceptación** (3-5 bullets concretos)
5. **¿Requiere SDD?** (por defecto `true` si involucra código o integración)
6. **¿A quién más le sirve?** (beneficiarios)

### ⚠️ Regla crítica: preguntar campo por campo

Cuando la feature reemplaza o migra datos existentes (Excel, formulario, sistema legacy), el intake DEBE recorrer CADA campo y preguntar:
- ¿Qué significa realmente? (no asumir por el nombre)
- ¿Cuándo se llena? (en creación, durante ejecución, al cierre)
- ¿Quién lo llena? (técnico, auxiliar, automático)
- ¿Qué valores son válidos? (binario, fecha, texto libre)

**No hacer esto causa specs incompletos desde el origen.** Ejemplo real: asumir que "Tiempo" significa duración sin preguntar, o que todos los campos se llenan al crear el registro cuando en realidad el sistema legacy es un workflow progresivo donde los campos se completan por etapas.

## Cómo usar OpenCode DESDE Hermes

### One-shot (tareas acotadas)

```bash
opencode run 'Ejecutá el flujo F2: implementar feature X.
Leé harness/specs/01_X/ y harness/learnings/implementer.md.'
--model <provider>/<model>
```

### Sesión interactiva (background + PTY)

```bash
# Iniciar OpenCode en el workdir del proyecto
terminal(command="opencode", workdir="~/proyecto", background=true, pty=true)

# Enviar prompts
process(action="submit", session_id="<id>", data="Implementar feature")

# Monitorear
process(action="poll", session_id="<id>")

# Salir con Ctrl+C — NUNCA usar /exit
process(action="write", session_id="<id>", data="\x03")
```

### Flujo completo con Hermes como líder

```
1. Hermes lee harness/feature_list.json → conoce estado actual
2. Hermes lee harness/.session → verifica sesión anterior cerrada
3. Si feature en spec-reviewed → Hermes lanza opencode con implementer
4. OpenCode implementa → reviewer → testing → ⏸ pausa humana
5. Humano prueba y autoriza → Hermes lanza release-manager
6. Hermes actualiza memoria/skills con lo aprendido
```

## Reglas duras

- ❌ NUNCA implementar código durante la fase de intake
- ❌ NUNCA inventar criterios de aceptación sin preguntar
- ❌ NUNCA usar `/exit` en OpenCode TUI — usar Ctrl+C
- ❌ NUNCA tocar código sin spec aprobado (`spec-reviewed`)
- ✅ Una sola feature a la vez
- ✅ Validar que `name` sea snake_case único
- ✅ El diálogo es conversacional, no interrogatorio
- ✅ Si la persona no sabe qué poner en acceptance, proponer ejemplos y validar
- ✅ **Los subagentes NO leen AGENTS.md automáticamente** — el líder debe incluir en el prompt: "Lee harness/learnings/common.md y harness/learnings/<tu_rol>.md antes de empezar"

## Pitfalls

- **Subagentes no leen AGENTS.md**: El líder DEBE incluir instrucciones explícitas en el prompt a OpenCode.
- **Encoding**: Siempre `utf-8` explícito al leer/escribir JSON. Usar `ensure_ascii=False`.
- **Modificar feature_list.json**: NUNCA con regex/sed. Siempre Python: leer → modificar → escribir.
- **Una feature a la vez**: Antes de lanzar cualquier agente, verificar que no hay otra en `in_progress` o `testing`.
- **Deploy + smoke test obligatorio**: El implementer DEBE desplegar y ejecutar smoke test. El reviewer rechaza sin evidencia.
- **Pruebas humanas (PH) obligatorias**: `design.md` DEBE incluir PH de tipos happy/sad/edge.
- **El spec-validator no es infalible**: Bugs de offset en strings y detalles de formato de archivos reales pueden pasar desapercibidos. **El implementer actúa como último validador al ejecutar con datos reales.**
- **El ciclo SDD no es lineal**: El implementer puede encontrar bugs que obligan a corregir el spec. Actualizar los specs sin miedo. Las versiones anteriores quedan en `.old.md`.
- **Sistemas legacy = sistemas vivos**: Al migrar un sistema basado en planillas o archivos, no se están importando datos muertos — se está migrando un workflow con tracking de estado. Tratar la fuente como sistema, no como volcado de datos.
