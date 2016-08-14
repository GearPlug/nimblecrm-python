from django.forms.models import model_to_dict
from django.views.generic import CreateView, UpdateView, DeleteView, ListView
from django.urls import reverse_lazy
from apps.plug.apps import APP_NAME as app_name
from apps.gp.models import Plug, Connection


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

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(CreatePlugView, self).form_valid(form)

    def get(self, *args, **kwargs):
        return super(CreatePlugView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return super(CreatePlugView, self).post(*args, **kwargs)

    def get_success_url(self):
        self.request.session['plug'] = model_to_dict(self.object)
        print(self.request.session['plug'])
        return self.success_url


class UpdatePlugView(UpdateView):
    model = Plug
    fields = ['name', ]
    template_name = '%s/update.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)

    def get(self, *args, **kwargs):
        print(self.request.session['plug'])
        return super(UpdatePlugView, self).get(*args, **kwargs)


class DeletePlugView(DeleteView):
    model = Plug
    template_name = '%s/delete.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)


class CreateConnectionView(CreateView):
    model = Connection
    template_name = 'connection/create.html'
