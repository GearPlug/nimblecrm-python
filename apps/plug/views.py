from django.views.generic import CreateView, UpdateView, DeleteView, ListView, FormView
from django.urls import reverse_lazy
from apps.plug.apps import APP_NAME as app_name
from apps.gp.models import Plug, PlugSpecification


class ListPlugView(ListView):
    model = Plug
    template_name = '%s/list.html' % app_name

    def get_context_data(self, **kwargs):
        context = super(ListPlugView, self).get_context_data(**kwargs)
        return context


class CreatePlugView(CreateView):
    model = Plug
    fields = ['name']
    template_name = '%s/create.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)

    def form_valid(self, form, *args, **kwargs):
        form.instance.user = self.request.user
        return super(CreatePlugView, self).form_valid(form)

    def get(self, *args, **kwargs):
        return super(CreatePlugView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return super(CreatePlugView, self).post(*args, **kwargs)

    def get_success_url(self):
        return self.success_url


class UpdatePlugView(UpdateView):
    model = Plug
    fields = ['name', 'connection', 'action']
    template_name = '%s/update.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)

    def get(self, *args, **kwargs):
        return super(UpdatePlugView, self).get(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        return super(UpdatePlugView, self).get_context_data(*args, **kwargs)


class UpdatePlugAddActionView(UpdatePlugView):
    fields = ['name', 'action']


class DeletePlugView(DeleteView):
    model = Plug
    template_name = '%s/delete.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)


class CreatePlugSpecificationsView(CreateView):
    model = PlugSpecification
    template_name = '%s/specifications/create.html' % app_name
    fields = ['plug', 'action_specification', 'value']
    success_url = reverse_lazy('%s:list' % app_name)

    def get(self, request, *args, **kwargs):
        return super(CreatePlugSpecificationsView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return super(CreatePlugSpecificationsView, self).post(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(CreatePlugSpecificationsView, self).get_context_data(*args, **kwargs)
        plug_id = self.kwargs['plug_id']
        plug = Plug.objects.filter(pk=plug_id).select_related('connection__connector').get(pk=plug_id)
        action_list = plug.connection.connector.action.all().filter(plug__action=plug.action).distinct()
        # if esp not in []
        action_specification_list = [esp for action in action_list for esp in action.action_specification.all()]
        context['action_specification_list'] = action_specification_list
        context['plug_id'] = plug_id
        return context


class UpdatePlugSpecificationsView(UpdateView):
    model = PlugSpecification
    template_name = '%s/specifications/update.html' % app_name
    fields = ['value']
    success_url = reverse_lazy('%s:list' % app_name)
