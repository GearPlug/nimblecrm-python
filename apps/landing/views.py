from django.views.generic import TemplateView, ListView
from django.urls import reverse_lazy
from django.db.models import Q
from allauth.account.views import SignupView
from apps.landing.forms import NameSignupForm
from apps.gp.models import Connector


class IndexView(TemplateView):
    template_name = 'landing/index.html'

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['signup_form'] = NameSignupForm()
        context['top_apps'] = Connector.objects.filter(Q(name__in=['slack', 'gmail', 'mysql', 'facebookleads',
                                                                   'googlespreadsheet', 'mailchimp']))
        return context


class AboutUsView(TemplateView):
    template_name = 'landing/aboutus.html'


class ContactUsView(TemplateView):
    template_name = 'landing/contactus.html'


class AppsView(ListView):
    template_name = 'landing/apps.html'
    model = Connector

    def get_queryset(self):
        return self.model.objects.filter(is_active=True)


class CustomSignup(SignupView):
    form_class = NameSignupForm
    template_name = 'landing/snippets/signup_form.html'
    http_method_names = 'post'
    success_url = reverse_lazy('home:dashboard')

    def form_invalid(self, form, **kwargs):
        return self.render_to_response(self.get_context_data(signup_form=form))
