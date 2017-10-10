from django.views.generic import TemplateView, ListView
from apps.landing.forms import NameSignupForm
from apps.gp.models import Connector


class IndexView(TemplateView):
    template_name = 'landing/index.html'

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['register_form'] = NameSignupForm()
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
