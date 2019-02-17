from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter


class GoogleOAuth2AdapterCustom(GoogleOAuth2Adapter):
    def get_callback_url(self, request, app):
        return 'http://localhost:3000/'
