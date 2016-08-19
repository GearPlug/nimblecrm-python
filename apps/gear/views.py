from django.views.generic import CreateView, UpdateView, DeleteView, ListView, FormView
from django.urls import reverse_lazy
from apps.gear.apps import APP_NAME as app_name
from apps.gp.models import Gear, Plug
from apps.gear.forms import MapForm


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
    fields = ['name', 'source', 'target']
    template_name = '%s/update.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)


class DeleteGearView(DeleteView):
    model = Gear
    template_name = '%s/delete.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)


class CreateGearMapView(FormView):
    template_name = 'mapping/create.html'
    form_class = MapForm

    def get(self, request, *args, **kwargs):
        gear_id = kwargs.pop('gear_id', 0)
        gear = Gear.objects.filter(pk=gear_id).select_related('source', 'target').get(pk=gear_id)
        source_plug = Plug.objects.filter(pk=gear.source.id).select_related('connection__connector').get(
            pk=gear.source.id)
        target_plug = Plug.objects.filter(pk=gear.target.id).select_related('connection__connector').get(
            pk=gear.target.id)
        print(target_plug.connection)
        return super(CreateGearMapView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return super(CreateGearMapView, self).post(request, *args, **kwargs)

    def form_valid(self, form, *args, **kwargs):
        return super(CreateGearMapView, self).form_valid(form, *args, **kwargs)

    def form_invalid(self, form, *args, **kwargs):
        return super(CreateGearMapView, self).form_valid(form, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(CreateGearMapView, self).get_context_data(**kwargs)
        return context

    def get_form_fields(self, *args, **kwargs):
        pass

    def mysql_as_target(self, *args, **kwargs):
        pass
