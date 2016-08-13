from django.views.generic import CreateView, UpdateView, DeleteView, ListView
from django.urls import reverse_lazy
from apps.gear.apps import APP_NAME as app_name
from apps.gp.models import Gear


class ListGearView(ListView):
    model = Gear
    template_name = '%s/list.html' % app_name

    def get_context_data(self, **kwargs):
        context = super(ListGearView, self).get_context_data(**kwargs)
        return context


class CreateGearView(CreateView):
    model = Gear
    fields = ['name', ]
    template_name = '%s/create.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(CreateGearView, self).form_valid(form)

    def get(self, *args, **kwargs):
        return super(CreateGearView, self).get(*args, **kwargs)


class UpdateGearView(UpdateView):
    model = Gear
    fields = ['name']
    template_name = '%s/update.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)


class DeleteGearView(DeleteView):
    model = Gear
    template_name = '%s/delete.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)
