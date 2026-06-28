"""Processor: detecção de eventos e política de gatilhos (anti-spam).

- ``processor.py``: traduz mudanças do GameState em ``Insight``s (Camada 1/2).
- ``triggers.py``: decide *quando* falar (cooldown, prioridade, dedupe).
"""

from voxcoach.processor.processor import Insight, Layer, Priority, Processor
from voxcoach.processor.triggers import TriggerPolicy

__all__ = ["Insight", "Layer", "Priority", "Processor", "TriggerPolicy"]
