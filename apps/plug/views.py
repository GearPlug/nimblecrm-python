from django.views.generic import CreateView, UpdateView, DeleteView, ListView, FormView
from django.urls import reverse_lazy
from apps.plug.apps import APP_NAME as app_name
from apps.gp.models import Plug, PlugSpecification
from extra_views import ModelFormSetView


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


class CreatePlugSpecificationsView(ModelFormSetView):
    model = PlugSpecification
    template_name = '%s/specifications/create.html' % app_name
    fields = ['plug', 'action_specification', 'value']
    success_url = reverse_lazy('%s:list' % app_name)
    max_num = 10
    extra = 0

    def get(self, request, *args, **kwargs):
        plug = Plug.objects.get(pk=self.kwargs['plug_id'])
        print(self.extra)
        self.extra = plug.action.action_specification.count()
        print("si")
        print(self.extra)
        return super(CreatePlugSpecificationsView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        plug = Plug.objects.get(pk=self.kwargs['plug_id'])
        self.extra = plug.action.action_specification.count()
        return super(CreatePlugSpecificationsView, self).post(request, *args, **kwargs)

    def form_valid(self, form, **kwargs):
        return super(CreatePlugSpecificationsView, self).form_valid(form, **kwargs)

    def form_invalid(self, form, **kwargs):
        return super(CreatePlugSpecificationsView, self).form_invalid(form, **kwargs)

    def get_queryset(self):
        return super(CreatePlugSpecificationsView, self).get_queryset().none()

    def get_context_data(self, *args, **kwargs):
        context = super(CreatePlugSpecificationsView, self).get_context_data(*args, **kwargs)
        plug = Plug.objects.filter(pk=self.kwargs['plug_id']).select_related('connection__connector').get(
            pk=self.kwargs['plug_id'])
        action_specification_list = [esp for esp in plug.action.action_specification.all()]
        # if esp not in []
        context['action_specification_list'] = action_specification_list
        context['plug_id'] = self.kwargs['plug_id']
        print("c")
        return context


class UpdatePlugSpecificationsView(UpdateView):
    model = PlugSpecification
    template_name = '%s/specifications/update.html' % app_name
    fields = ['value']
    success_url = reverse_lazy('%s:list' % app_name)
