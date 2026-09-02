"""
MITSU Android Service — Background TTS and proactive messaging.
This service runs in the background and handles voice output.
"""
from jnius import autoclass
from android import service

# Android service classes
PythonService = autoclass('org.kivy.android.PythonService')
String = autoclass('java.lang.String')


class MitsuService:
    """Background service for Mitsu Android."""
    
    def __init__(self):
        self.is_running = False
    
    def start(self):
        """Start the background service."""
        self.is_running = True
        # Service will be handled by Kivy's service system
    
    def stop(self):
        """Stop the background service."""
        self.is_running = False


# Service entry point
def start_service():
    """Start the Mitsu background service."""
    service.start(
        'MitsuService',
        'Mitsu background service for TTS and proactive messaging'
    )
