# middleware.py
import threading

_thread_locals = threading.local()

class CurrentUserMiddleware:
    """
    Stores request.user in thread-local so signals can pick it up.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = getattr(request, 'user', None)
        return self.get_response(request)

def get_current_user():
    return getattr(_thread_locals, 'user', None)
