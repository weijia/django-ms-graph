import yaml
from requests_oauthlib import OAuth2Session
import os
import time

# This is necessary for testing with non-HTTPS localhost
# Remove this if deploying to production

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# This is necessary because Azure does not guarantee
# to return scopes in the same case and order as requested
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
os.environ['OAUTHLIB_IGNORE_SCOPE_CHANGE'] = '1'


# Load the oauth_settings.yml file
stream = open(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'oauth_settings.yml'), 'r')
settings = yaml.load(stream)
authorize_url = '{0}{1}'.format(settings['authority'], settings['authorize_endpoint'])
token_url = '{0}{1}'.format(settings['authority'], settings['token_endpoint'])


# Method to generate a sign-in url
def get_sign_in_url():
    try:
        from djangoautoconf.local_key_manager import get_local_key
        app_id = get_local_key("onedrive.client_id")
    except:
        app_id = settings['app_id']
    # Initialize the OAuth client
    aad_auth = OAuth2Session(app_id,
                             scope=unicode(settings['scopes']),
                             redirect_uri=settings['redirect'])

    sign_in_url, state = aad_auth.authorization_url(authorize_url, prompt='login')

    return sign_in_url, state


# Method to exchange auth code for access token
def get_token_from_code(callback_url, expected_state):
    # Initialize the OAuth client
    try:
        from djangoautoconf.local_key_manager import get_local_key
        app_id = get_local_key("onedrive.client_id")
        app_secret = get_local_key("onedrive.client_secret")
    except ImportError:
        app_id = settings['app_id']
        app_secret = settings['app_secret']
    aad_auth = OAuth2Session(app_id,
                             state=expected_state,
                             scope=settings['scopes'],
                             redirect_uri=settings['redirect'])

    token = aad_auth.fetch_token(token_url,
                                 client_secret=app_secret,
                                 authorization_response=callback_url)

    return token


def store_token(request, token):
    request.session['oauth_token'] = token


def store_user(request, user):
    request.session['user'] = {
        'is_authenticated': True,
        'name': user['displayName'],
        'email': user['mail'] if (user['mail'] is not None) else user['userPrincipalName']
    }


def get_token(request):
    token = request.session['oauth_token']
    if token is not None:
        # Check expiration
        now = time.time()
        # Subtract 5 minutes from expiration to account for clock skew
        expire_time = token['expires_at'] - 300
        if now >= expire_time:
            # Refresh the token
            aad_auth = OAuth2Session(settings['app_id'],
                                     token=token,
                                     scope=settings['scopes'],
                                     redirect_uri=settings['redirect'])

            refresh_params = {
                'client_id': settings['app_id'],
                'client_secret': settings['app_secret'],
            }
            new_token = aad_auth.refresh_token(token_url, **refresh_params)

            # Save new token
            store_token(request, new_token)

            # Return new access token
            return new_token

        else:
            # Token still valid, just return it
            return token


def remove_user_and_token(request):
    if 'oauth_token' in request.session:
        del request.session['oauth_token']

    if 'user' in request.session:
        del request.session['user']
