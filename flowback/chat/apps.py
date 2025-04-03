from django.apps import AppConfig


class ChatConfig(AppConfig):
    name = 'flowback.chat'

    def ready(self):
        import flowback.chat.signals
