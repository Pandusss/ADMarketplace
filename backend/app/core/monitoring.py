"""
No-op monitoring module.
Any alert_* call becomes a no-op.
"""

class Monitoring:
    def __getattr__(self, name: str):
        def _noop(*args, **kwargs):
            return None
        return _noop

monitoring = Monitoring()
