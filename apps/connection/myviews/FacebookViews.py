from django.views.generic import TemplateView, UpdateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from apiconnector.settings import FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, FACEBOOK_GRAPH_VERSION
from apps.gp.views import TemplateViewWithPost
from apps.gp.models import StoredData
import facebook
import json
import requests
import hmac
import hashlib

base_graph_url = 'https://graph.facebook.com'


# Vista base de facebook. Hace request utilizando el graph api.
class AJAXFacebookBaseView(TemplateViewWithPost):
    template_name = 'connection/facebook/ajax_facebook_select.html'
    has_objects = False

    def get_context_data(self, *args, **kwargs):
        context = super(AJAXFacebookBaseView, self).get_context_data(**kwargs)
        token = self.request.POST.get('user_access_token', '')
        url = kwargs.pop('url', '')
        object_list = facebook_request(url, token)
        if object_list:
            self.has_objects = True
        context['object_list'] = object_list
        return context


class AJAXFacebookGetAvailableConnectionsView(AJAXFacebookBaseView):
    template_name = 'connection/facebook/ajax_facebook_select.html'

    def get_context_data(self, *args, **kwargs):
        kwargs['url'] = 'me/accounts'
        context = super(AJAXFacebookGetAvailableConnectionsView, self).get_context_data(**kwargs)
        return context


class AJAXFacebookGetAvailableFormsView(AJAXFacebookBaseView):
    template_name = 'connection/facebook/ajax_facebook_select.html'

    def get_context_data(self, *args, **kwargs):
        connection_id = self.request.POST.get('connection_id', '')
        kwargs['url'] = '%s/leadgen_forms' % connection_id
        context = super(AJAXFacebookGetAvailableFormsView, self).get_context_data(**kwargs)
        return context


class AJAXFacebookGetAvailableLeadsView(AJAXFacebookBaseView):
    template_name = 'connection/facebook/ajax_facebook_select.html'
    get_data = False

    def get_context_data(self, *args, **kwargs):
        self.get_data = self.request.POST.get('get_data', False)
        form_id = self.request.POST.get('form_id', '')
        kwargs['url'] = '%s/leads' % form_id
        context = super(AJAXFacebookGetAvailableLeadsView, self).get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        if self.get_data:
            return super(TemplateView, self).render_to_response(context)
        return JsonResponse({'data': self.has_objects})


# Facebook
def generate_app_secret_proof(app_secret, access_token):
    h = hmac.new(
        app_secret.encode('utf-8'),
        msg=access_token.encode('utf-8'),
        digestmod=hashlib.sha256
    )
    return h.hexdigest()


# Does a facebook request. Returns an array with the response or an empty array
def facebook_request(url, token):
    graph = facebook.GraphAPI(version=FACEBOOK_GRAPH_VERSION)  # Crea el objeto para interactuar con GRAPH API
    graph.access_token = graph.get_app_access_token(FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)  # ACCESS TOKEN DE LA APP
    r = requests.get('%s/v%s/%s' % (base_graph_url, FACEBOOK_GRAPH_VERSION, url),
                     params={'access_token': token,
                             'appsecret_proof': generate_app_secret_proof(FACEBOOK_APP_SECRET, token)})
    #print(r.url)
    try:
        return json.loads(r.text)['data']
    except Exception as e:
        print(e)
        return []


def extend_facebook_token(token):
    url = 'oauth/access_token'
    graph = facebook.GraphAPI(version=FACEBOOK_GRAPH_VERSION)  # Crea el objeto para interactuar con GRAPH API
    graph.access_token = graph.get_app_access_token(FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)  # ACCESS TOKEN DE LA APP
    r = requests.get('%s/v%s/%s' % (base_graph_url, FACEBOOK_GRAPH_VERSION, url),
                     params={'grant_type': 'fb_exchange_token',
                             'client_id': FACEBOOK_APP_ID,
                             'client_secret': FACEBOOK_APP_SECRET,
                             'fb_exchange_token': token})
    try:
        return json.loads(r.text)['access_token']
    except Exception as e:
        print(e)
        return ''
