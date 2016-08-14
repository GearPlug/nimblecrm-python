from django.views.generic import CreateView, UpdateView, DeleteView, ListView, FormView
from django.urls import reverse_lazy
from apps.connection.apps import APP_NAME as app_name
from apps.gp.models import Connection, Connector, FacebookConnection, MySQLConnection
from apps.connection.forms import SelectConnectorForm
from apps.gp.connector_enum import ConnectorEnum


class ListConnectionView(ListView):
    model = Connection
    template_name = '%s/list.html' % app_name

    def get_context_data(self, **kwargs):
        context = super(ListConnectionView, self).get_context_data(**kwargs)
        return context


class CreateConnectionView(CreateView):
    model = Connection
    fields = []
    template_name = '%s/create.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(CreateConnectionView, self).form_valid(form)

    def get(self, *args, **kwargs):
        if self.kwargs['connector_id'] is not None:
            self.model, self.fields = ConnectorEnum.get_connector_data(self.kwargs['connector_id'])
        return super(CreateConnectionView, self).get(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(CreateConnectionView, self).get_context_data(**kwargs)
        context['connection'] = ConnectorEnum.get_connector(self.kwargs['connector_id']).name
        return context


class UpdateConnectionView(UpdateView):
    model = Connection
    fields = ['name']
    template_name = '%s/update.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)


class DeleteConnectionView(DeleteView):
    model = Connection
    template_name = '%s/delete.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)


# # Esto va en una clase para extender
# class FormListView(FormMixin, ListView):
#     def get(self, request, *args, **kwargs):
#         # From ProcessFormMixin
#         form_class = self.get_form_class()
#         self.form = self.get_form(form_class)
#
#         # From BaseListView
#         self.object_list = self.get_queryset()
#         allow_empty = self.get_allow_empty()
#         if not allow_empty and len(self.object_list) == 0:
#             raise Http404(_(u"Empty list and '%(class_name)s.allow_empty' is False.")
#                           % {'class_name': self.__class__.__name__})
#
#         context = self.get_context_data(object_list=self.object_list, form=self.form)
#         return self.render_to_response(context)
#
#     def post(self, request, *args, **kwargs):
#         return self.get(request, *args, **kwargs)


class ListConnectorView(FormView):
    form_class = SelectConnectorForm
    template_name = '%s/list_connector.html' % app_name
