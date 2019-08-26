from django.contrib.auth.models import User
from social_django.models import UserSocialAuth


class UserNotExists(Exception):
    pass


class SocialAuthStorage(object):
    def __init__(self, provider):
        super(SocialAuthStorage, self).__init__()
        self.provider = provider

    def save_token(self, user_email, token):
        user = User.objects.filter(email=user_email)
        if user.exists():
            social_auth, is_created = UserSocialAuth.objects.get_or_create(
                user=user, provider=self.provider)
            if is_created:
                social_auth.uid = user_email
                social_auth.extra_data = {"token": token}
                social_auth.save()
        else:
            raise UserNotExists

    def get_refresh_token(self, user_email):
        auth_data_filter = UserSocialAuth.objects.filter(
            user=User.objects.filter(email=user_email),
            provider=self.provider)
        if auth_data_filter.exists():
            return auth_data_filter[0].extra_data["token"]["refresh_token"]
        raise UserNotExists
