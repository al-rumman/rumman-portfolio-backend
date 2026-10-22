from rest_framework.throttling import SimpleRateThrottle


class IPRateThrottle(SimpleRateThrottle):
    """IP onujayi rate limit. Rate settings.py theke ashe."""

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


class LikeThrottle(IPRateThrottle):
    scope = 'like'


class CommentThrottle(IPRateThrottle):
    scope = 'comment'


class ContactThrottle(IPRateThrottle):
    scope = 'contact'