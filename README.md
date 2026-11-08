# Issue Orchestrator E2E pilot

Временный публичный репозиторий для проверки очереди GitHub Issues через Codex Desktop.
Содержит только синтетический Python-код, без секретов и настоящих проектов.

## Использование

```python
from converter import to_celsius, to_fahrenheit

print(to_fahrenheit(0))  # 32.0
print(to_celsius(212))   # 100.0
```

Обе функции принимают числа `int` и `float` и возвращают `float`.
Логические значения `bool` и другие типы вызывают `TypeError`, а `nan` и
бесконечность — `ValueError`. Целое число, слишком большое для преобразования
в `float`, вызывает `OverflowError`.

## Тесты

```powershell
py -3.14 -m unittest discover -s tests -v
```
