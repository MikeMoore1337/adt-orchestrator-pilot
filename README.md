# Issue Orchestrator E2E pilot

Исходная конфигурация оригинального Issue-Orchestrator 0.10.0 (Issue #570) подготовлена, но **движок не активирован**. До первого рабочего сеанса PR #9 должен быть вручную слит в защищённую ветку `main`: `seed_ref: origin/main` намеренно исключает запуск с неполной базой. Состояние: `ORIGINAL_ENGINE_NAMESPACED_SOURCE_CI_PASS / WSL2_OS_PROBE_PENDING / E2E_NOT_VERIFIED`. См. [отдельные правила](docs/UPSTREAM_ORCHESTRATOR_PILOT.md). Ранее завершённые Issues #1-#3 относились к ручному Codex Desktop, а не к автономному исходному движку.

Временный публичный репозиторий для проверки оригинального Issue-Orchestrator через Codex CLI в WSL2, с авторизацией ChatGPT.
Содержит только синтетический Python-код, без секретов и настоящих проектов.

## Использование

```python
from converter import from_kelvin, to_celsius, to_fahrenheit, to_kelvin

print(to_fahrenheit(0))  # 32.0
print(to_celsius(212))   # 100.0
print(to_kelvin(0))      # 273.15
print(from_kelvin(0))    # -273.15
```

Все функции принимают числа `int` и `float` и возвращают `float`.
Логические значения `bool` и другие типы вызывают `TypeError`, а `nan` и
бесконечность — `ValueError`. Целое число, слишком большое для преобразования
в `float`, вызывает `OverflowError`.

`to_kelvin(celsius)` переводит градусы Цельсия в кельвины по формуле
`celsius + 273.15`, а `from_kelvin(kelvin)` выполняет обратное преобразование:
`kelvin - 273.15`. Температуры ниже абсолютного нуля (меньше `-273.15 °C`
или `0 K` соответственно) вызывают `ValueError`. На границе допустимы
`to_kelvin(-273.15) == 0.0` и `from_kelvin(0) == -273.15`.

## Тесты

```powershell
py -3.14 -m unittest discover -s tests -v
```


## Происхождение защитных хуков

Генерируемые скрипты `.codex/`, `.githooks/pre-push` и `scripts/` содержат части оригинального Issue-Orchestrator 0.10.0 под Apache-2.0. Оригинальные `LICENSE` и `NOTICE` сохранены в [third_party/issue-orchestrator](third_party/issue-orchestrator/README.md). Код очереди и оркестратора не копировался.
