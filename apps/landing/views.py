from django.shortcuts import render
from django.views.generic import TemplateView


class IndexView(TemplateView):
    template_name = 'landing/index.html'


class AboutUsView(TemplateView):
    template_name = 'landing/aboutus.html'


class ContactUsView(TemplateView):
    template_name = 'landing/contactus.html'


class AppsView(TemplateView):
    template_name = 'landing/apps.html'
