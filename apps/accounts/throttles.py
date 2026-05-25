from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    scope = "auth"

    def get_cache_key(self, request, view) -> str:
        username = request.data.get("username", "").lower()
        ip = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": f"{ip}:{username}"}
