from .scheduler import generate_bills

class RunBillsOnEveryVisitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Run generate_bills() on every request
        generate_bills()
        response = self.get_response(request)
        return response
