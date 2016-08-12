from django.shortcuts import redirect
from django.views.generic import TemplateView
from apps.user.views import LoginView


class DashBoardView(TemplateView):
    template_name = 'main/../../templates/home/dashboard.html'

    def get(self,*args, **kwargs):
        return super(DashBoardView, self).get(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DashBoardView, self).get_context_data(**kwargs)
        context["message"] = "Hello!"
        return context


class HomeView(LoginView):
    template_name = 'main/../../templates/home/index.html'
    success_url = '/dashboard/'

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated():
            return redirect(self.get_success_url())
        return super(HomeView, self).get(*args, **kwargs)