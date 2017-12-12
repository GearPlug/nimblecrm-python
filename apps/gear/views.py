from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import modelform_factory, modelformset_factory
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, FormView
from django.views.generic.edit import FormMixin
from django.http.response import JsonResponse, HttpResponseForbidden, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from apps.gear.apps import APP_NAME as app_name
from apps.gear.forms import MapForm, SendHistoryForm, DownloadHistoryForm, FiltersForm
from apps.gp.enum import ConnectorEnum
from apps.gp.tasks import update_plug
from apps.gp.models import Gear, Plug, StoredData, GearMap, GearMapData, GearGroup, GearFilter
from apps.history.models import DownloadHistory, SendHistory
from oauth2client import client
import httplib2
import json
from django.apps import apps

class ListGearView(LoginRequiredMixin, ListView):
    """
    Lists all gears related to the authenticated user.

    - Is not called in the wizard.
    """
    model = GearGroup
    template_name = 'gear/list.html'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        context = super(ListGearView, self).get_context_data(**kwargs)
        gear_form = modelform_factory(Gear, fields=('name', 'gear_group'))
        gear_form.base_fields["gear_group"].queryset = GearGroup.objects.filter(user=self.request.user)
        context['gear_form'] = gear_form
        context['geargroup_form'] = modelform_factory(GearGroup, fields=('name',))
        return context

    def get_queryset(self):
        return self.model.objects.filter(
            user=self.request.user).prefetch_related('gear')


class CreateGearView(LoginRequiredMixin, CreateView):
    """
    Creates an empty gear and associate it to the authenticated user.

    - Calls the connector list as a source.

    """
    model = Gear
    template_name = 'gear/create.html'
    fields = ['name', 'gear_group']
    login_url = '/accounts/login/'
    success_url = reverse_lazy('connection:connector_list',
                               kwargs={'type': 'source'})

    def get(self, request, *args, **kwargs):
        request.session['gear_id'] = None
        return super(CreateGearView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        self.request.session['gear_id'] = self.object.id
        return super(CreateGearView, self).get_success_url()

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super(CreateGearView, self).form_valid(form)
        if self.request.is_ajax():
            self.object = form.save()
            response = JsonResponse({'result': 'created', 'next_url': self.get_success_url()})
        GearMap.objects.create(gear=self.object)
        return response

    def get_context_data(self, **kwargs):
        context = super(CreateGearView, self).get_context_data(**kwargs)
        context['object_name'] = self.model.__name__
        return context

    def get_form(self, form_class=None):
        form = super(CreateGearView, self).get_form(form_class=form_class)
        form.fields["gear_group"].queryset = GearGroup.objects.filter(
            user=self.request.user)
        return form


class UpdateGearView(LoginRequiredMixin, UpdateView):
    """
    Updates the selected gear.

    - Calls the connector list as a source.

    """
    model = Gear
    template_name = 'gear/update.html'
    fields = ['name', 'gear_group']
    login_url = '/accounts/login/'
    success_url = reverse_lazy('connection:connector_list',
                               kwargs={'type': 'source'})

    def get(self, request, *args, **kwargs):
        request.session['gear_id'] = self.kwargs.get('pk', None)
        return super(UpdateGearView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        try:
            return self.model.objects.filter(pk=self.kwargs.get('pk', None),
                                             user=self.request.user)
        except Exception as e:
            raise

    def get_context_data(self, **kwargs):
        context = super(UpdateGearView, self).get_context_data(**kwargs)
        context['object_name'] = self.model.__name__
        return context

    def get_form(self, form_class=None):
        form = super(UpdateGearView, self).get_form(form_class=form_class)
        form.fields["gear_group"].queryset = GearGroup.objects.filter(
            user=self.request.user)
        return form


class CreateGearGroupView(CreateView):
    model = GearGroup
    template_name = 'gear/snippets/gear_form.html'
    fields = ['name', ]
    login_url = '/accounts/login/'
    success_url = reverse_lazy('gear:list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        if self.request.is_ajax():
            self.object = form.save()
            return JsonResponse({'result': 'created', 'next_url': self.get_success_url()})
        return super(CreateGearGroupView, self).form_valid(form)

    def form_invalid(self, form):
        return super(CreateGearGroupView, self).form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(CreateGearGroupView, self).get_context_data(**kwargs)
        context['object_name'] = self.model.__name__
        return context


class UpdateGearGroupView(UpdateView):
    model = GearGroup
    template_name = 'gear/update.html'
    fields = ['name', ]
    login_url = '/accounts/login/'
    success_url = reverse_lazy('gear:list')

    def get(self, request, *args, **kwargs):
        request.session['gear_id'] = self.kwargs.get('pk', None)
        return super(UpdateGearGroupView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        try:
            return self.model.objects.filter(pk=self.kwargs.get('pk', None),
                                             user=self.request.user)
        except Exception as e:
            raise

    def get_context_data(self, **kwargs):
        context = super(UpdateGearGroupView, self).get_context_data(**kwargs)
        context['object_name'] = self.model.__name__
        return context


class DeleteGearView(DeleteView):
    """
    Deletes the selected gear. Should not remove the gear from the database but mark it as deleted instead.

    """
    model = Gear
    template_name = '%s/delete.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)


class CreateGearMapView(FormView, LoginRequiredMixin):
    """
    Creates a Map for the selected gear.

    """
    login_url = '/accounts/login/'
    template_name = 'gear/map.html'
    form_class = MapForm
    form_field_list = []
    source_object_list = []
    success_url = reverse_lazy('%s:list' % app_name)
    exists = False

    def get(self, request, *args, **kwargs):
        """
        Define las variables source_object_list y form_field_list, necesarias para el mapeo.
        """
        gear_id = kwargs.pop('gear_id', 0)
        gear = Gear.objects.filter(pk=gear_id).select_related('source', 'target').get(pk=gear_id)
        source_plug = Plug.objects.filter(pk=gear.source.id).select_related('connection__connector').get(
            pk=gear.source.id)
        target_plug = Plug.objects.filter(pk=gear.target.id).select_related('connection__connector').get(
            pk=gear.target.id)
        # Source options
        self.source_object_list = self.get_available_source_fields(source_plug)
        # Target fields
        self.form_field_list = self.get_target_field_list(target_plug)
        self.gear_map = GearMap.objects.filter(gear=gear).first()
        return super(CreateGearMapView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        gear_id = kwargs.pop('gear_id', 0)
        gear = Gear.objects.filter(pk=gear_id).select_related('source', 'target').get(pk=gear_id)
        target_plug = Plug.objects.filter(pk=gear.target.id).select_related('connection__connector').get(
            pk=gear.target.id)
        self.form_field_list = self.get_target_field_list(target_plug)
        self.gear_map = GearMap.objects.filter(gear=gear).first()
        return super(CreateGearMapView, self).post(request, *args, **kwargs)

    def form_valid(self, form, *args, **kwargs):
        all_data = GearMapData.objects.filter(gear_map=self.gear_map)
        for f, v in form.cleaned_data.items():
            try:
                field = all_data.get(target_name=f)
                if isinstance(v, str) and (v == '' or v.isspace()):
                    field.delete()
                else:
                    if field.source_value != v:
                        field.source_value = v
                        field.save(update_fields=['source_value'])
            except GearMapData.DoesNotExist:
                if v is not None and (v != '' or not v.isspace()):
                    GearMapData.objects.create(gear_map=self.gear_map, target_name=f, source_value=v)
            except Exception as e:
                raise
        self.gear_map.gear.is_active = True
        self.gear_map.gear.save()
        return super(CreateGearMapView, self).form_valid(form, *args, **kwargs)

    def form_invalid(self, form, *args, **kwargs):
        return super(CreateGearMapView, self).form_valid(form, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(CreateGearMapView, self).get_context_data(**kwargs)
        context['source_object_list'] = self.source_object_list
        context['action'] = 'Create' if self.gear_map is None else 'Update'
        return context

    def get_form(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = form_class(extra=self.form_field_list, **self.get_form_kwargs())
        if self.request.method == 'GET' and self.gear_map is not None:
            all_data = GearMapData.objects.filter(gear_map=self.gear_map)
            for label, field in form.fields.items():
                try:
                    field.initial = all_data.get(target_name=label).source_value
                except:
                    pass
        return form

    def get_available_source_fields(self, plug):
        c = ConnectorEnum.get_connector(plug.connection.connector.id)
        if c == ConnectorEnum.GoogleContacts:
            self.google_contacts_controller.create_connection(plug.connection.related_connection, plug)
            return ['%%{0}%%'.format(field) for field in self.google_contacts_controller.get_contact_fields()]
        return ['%%{0}%%'.format(item['name']) for item in
                StoredData.objects.filter(plug=plug, connection=plug.connection).values('name').distinct()]

    def get_target_field_list(self, plug):
        c = ConnectorEnum.get_connector(plug.connection.connector.id)
        controller_class = ConnectorEnum.get_controller(c)
        related = plug.connection.related_connection
        controller = controller_class(connection=related, plug=plug)
        if controller.test_connection():
            return controller.get_mapping_fields()
        return []


class ActivityView(LoginRequiredMixin, ListView):
    model = SendHistory
    template_name = 'gear/activity.html'
    login_url = '/accounts/login/'

    def get_queryset(self):
        gear_list = Gear.objects.filter(user=self.request.user)
        recent_activity = self.model.objects.filter(gear_id__in=gear_list).order_by('-id')[:10]
        obj_list = []
        for item in recent_activity:
            gear = gear_list.get(pk=item.gear_id)
            obj_list.append({'gear_id': item.gear_id, 'source_connector': gear.source.connection.connector.name,
                             'target_connector': gear.target.connection.connector.name,
                             'action_source': gear.source.action.name,
                             'action_target': gear.target.action.name})
        return obj_list


class GearSendHistoryView(FormMixin, LoginRequiredMixin, ListView, ):
    model = SendHistory
    form_class = SendHistoryForm
    template_name = 'gear/send_history.html'
    login_url = '/accounts/login/'

    def get_queryset(self, **kwargs):
        order = 'date'
        if self.request.method == "POST":
            if 'date_from' in self.request.POST and self.request.POST['date_from']:
                if 'date_to' in self.request.POST and self.request.POST['date_to']:
                    kwargs['date__range'] = (self.request.POST['date_from'], self.request.POST['date_to'])
                else:
                    kwargs['date__gte'] = self.request.POST['date_from']
            elif 'date_to' in self.request.POST and self.request.POST['date_to']:
                kwargs['date__lte'] = self.request.POST['date_to']
            if 'order' in self.request.POST and self.request.POST['order'] == 'desc':
                order = '-date'
            if 'sent' in kwargs and kwargs['sent'] == '0':
                del kwargs['sent']
            del kwargs['date_from']
            del kwargs['date_to']
            del kwargs['order']
        return [{'connection': json.loads(item.connection)[0]['fields']['name'],
                 'data': [{'name': k, 'value': v} for k, v in json.loads(item.data).items()],
                 'date': item.date,
                 'connector_id': item.connector_id,
                 'connector_name': ConnectorEnum.get_connector(item.connector_id).name,
                 'sent': item.sent,
                 'response': item.response,
                 'identifier': item.identifier,
                 'id': item.id,
                 } for item in self.model.objects.filter(gear_id=self.kwargs['pk'], **kwargs).order_by(order)]

    def get(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated or Gear.objects.get(pk=self.kwargs['pk']).user != self.request.user:
                return HttpResponseForbidden()
        except:
            return HttpResponseForbidden()
        return super(GearSendHistoryView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(GearSendHistoryView, self).get_context_data(**kwargs)
        context['form'] = self.get_form()
        return context

    def post(self, request, **kwargs):
        if not request.user.is_authenticated and Gear.objects.get(self.kwargs['pk']).user != self.request.user:
            return HttpResponseForbidden()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.object_list = self.get_queryset(**form.cleaned_data)
        context = self.get_context_data()
        return self.render_to_response(context)
        # return super(GearSendHistoryView, self).form_valid(form)


class GearActivitiesHistoryView(FormMixin, LoginRequiredMixin, ListView, ):
    model = SendHistory
    form_class = SendHistoryForm
    template_name = 'gear/send_history.html'
    login_url = '/accounts/login/'

    def get_queryset(self, **kwargs):
        order = 'date'
        if self.request.method == "POST":
            if 'date_from' in self.request.POST and self.request.POST['date_from']:
                if 'date_to' in self.request.POST and self.request.POST['date_to']:
                    kwargs['date__range'] = (self.request.POST['date_from'], self.request.POST['date_to'])
                else:
                    kwargs['date__gte'] = self.request.POST['date_from']
            elif 'date_to' in self.request.POST and self.request.POST['date_to']:
                kwargs['date__lte'] = self.request.POST['date_to']
            if 'order' in self.request.POST and self.request.POST['order'] == 'desc':
                order = '-date'
            if 'sent' in kwargs and kwargs['sent'] == '0':
                del kwargs['sent']
            del kwargs['date_from']
            del kwargs['date_to']
            del kwargs['order']
        gears = list(Gear.objects.filter(user_id=self.request.user.id).values_list('id', flat=True))
        return [{'connection': json.loads(item.connection)[0]['fields']['name'],
                 'data': [{'name': k, 'value': v} for k, v in json.loads(item.data).items()],
                 'date': item.date,
                 'connector_id': item.connector_id,
                 'connector_name': ConnectorEnum.get_connector(item.connector_id).name,
                 'sent': item.sent,
                 'response': item.response,
                 'identifier': item.identifier,
                 'id': item.id,
                 } for item in self.model.objects.filter(gear_id__in=gears, **kwargs).order_by(order)]

    def get(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return HttpResponseForbidden()
        except:
            return HttpResponseForbidden()
        return super(GearActivitiesHistoryView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(GearActivitiesHistoryView, self).get_context_data(**kwargs)
        context['form'] = self.get_form()
        context['recent'] = True
        return context

    def post(self, request, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.object_list = self.get_queryset(**form.cleaned_data)
        context = self.get_context_data()
        return self.render_to_response(context)
        # return super(GearSendHistoryView, self).form_valid(form)


class GearDownloadHistoryView(GearSendHistoryView):
    model = DownloadHistory
    form_class = DownloadHistoryForm
    template_name = 'gear/download_history.html'
    login_url = '/accounts/login/'

    def get_queryset(self, **kwargs):
        order = 'date'
        if self.request.method == "POST":
            if 'date_from' in self.request.POST and self.request.POST['date_from']:
                if 'date_to' in self.request.POST and self.request.POST['date_to']:
                    kwargs['date__range'] = (self.request.POST['date_from'], self.request.POST['date_to'])
                else:
                    kwargs['date__gte'] = self.request.POST['date_from']
            elif 'date_to' in self.request.POST and self.request.POST['date_to']:
                kwargs['date__lte'] = self.request.POST['date_to']
            if 'order' in self.request.POST and self.request.POST['order'] == 'desc':
                order = '-date'
            del kwargs['date_from']
            del kwargs['date_to']
            del kwargs['order']
        return [{'connection': json.loads(item.connection)[0]['fields']['name'],
                 'raw': [{'name': k, 'value': v} for k, v in json.loads(item.raw).items()],
                 'date': item.date,
                 'connector_id': item.connector_id,
                 'connector_name': ConnectorEnum.get_connector(item.connector_id).name,
                 'id': item.id,
                 } for item in self.model.objects.filter(gear_id=self.kwargs['pk'], **kwargs).order_by(order)]


class GearFiltersView(FormView, LoginRequiredMixin):
    login_url = '/accounts/login/'
    template_name = 'gear/filters.html'
    form_class = FiltersForm
    success_url = reverse_lazy('connection:connector_list', kwargs={'type': 'target'})
    exists = False

    def post(self, request, *args, **kwargs):
        modelformset = modelformset_factory(GearFilter, FiltersForm, extra=0, min_num=1, max_num=100, can_delete=True)
        formset = modelformset(self.request.POST, queryset=GearFilter.objects.filter(gear_id=kwargs['pk']))
        if formset.is_valid():
            filters = formset.save(commit=False)
            for filter in filters:
                _gear = Gear.objects.get(id=kwargs['pk'])
                filter.gear = _gear
                filter.save()
            for filter in formset.deleted_forms:
                if 'DELETE' in filter.cleaned_data and filter.cleaned_data['DELETE'] is True:
                    filter.cleaned_data['id'].delete()
        else:
            print("no es valido")
        return HttpResponseRedirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super(GearFiltersView, self).get_context_data(**kwargs)
        modelformset = modelformset_factory(GearFilter, FiltersForm, extra=0, min_num=1, max_num=100, can_delete=True)
        formset = modelformset(queryset=GearFilter.objects.filter(gear_id=self.kwargs['pk']))
        context['formset'] = formset
        return context


def gear_toggle(request, gear_id):
    if request.is_ajax() is True and request.method == 'POST':
        try:
            g = Gear.objects.get(pk=gear_id)
            if g.user == request.user:
                source = g.source
                target = g.target

                if not source or not target:
                    return JsonResponse({'data': 'Error'})

                connector_source = ConnectorEnum.get_connector(source.connection.connector.id)
                controller_class = ConnectorEnum.get_controller(connector_source)
                controller = controller_class(connection=source.connection.related_connection, plug=source)
                if not controller.test_connection():
                    return JsonResponse({'data': 'Error'})

                connector_target = ConnectorEnum.get_connector(target.connection.connector.id)
                controller_class = ConnectorEnum.get_controller(connector_target)
                controller = controller_class(connection=target.connection.related_connection, plug=target)
                if not controller.test_connection():
                    return JsonResponse({'data': 'Error'})

                if g.gear_map.is_active is True:
                    g.is_active = not g.is_active
                    g.save()
                else:
                    return JsonResponse(
                        {'data': 'There\'s no active gear map.'})
            else:
                return JsonResponse(
                    {'data': "You don't have permission to toggle this gear."})
        except Gear.DoesNotExist:
            return JsonResponse({'data': 'Error invalid gear id.'})
        except GearMap.DoesNotExist:
            return JsonResponse({'data': 'There\'s no active gear map.'})
        return JsonResponse({'data': g.is_active})
    return JsonResponse({'data': 'request needs to be ajax'})


def get_authorization(request):
    credentials = client.OAuth2Credentials.from_json(
        request.session['google_credentials'])
    return credentials.authorize(httplib2.Http())


def retry_send_history(request):
    if request.is_ajax() is True and request.method == 'POST':
        history_id = request.POST.get('history_id')
        history = SendHistory.objects.get(pk=history_id)
        d = json.loads(history.connection)
        model = apps.get_model(*d[0]['model'].split("."))
        connection = model.objects.get(pk=d[0]['pk'])
        controller = ConnectorEnum.get_controller(ConnectorEnum.get_connector(connection.connection.connector_id))
        controller_instance = controller(connection.connection.related_connection, connection.connection.plug)
        data = json.loads(history.data)
        response = controller_instance.send_stored_data([data])
        history.identifier = response[0]['identifier']
        history.sent = response[0]['sent']
        history.tries = history.tries + 1
        history.save()
        return JsonResponse({'data': True})
    return JsonResponse({'data': False})


def set_gear_id_to_session(request):
    if request.is_ajax() is True and request.method == 'POST':
        request.session['gear_id'] = request.POST.get('gear_id', None)
        return JsonResponse({'data': True})
    return JsonResponse({'data': False})

@csrf_exempt
def manual_queue(request, gear_id):
    if request.is_ajax() is True and request.method == 'POST':
        try:
            g = Gear.objects.get(pk=gear_id)
            if g.user == request.user:
                source = g.source
                target = g.target
                if not source or not target:
                    return JsonResponse({'data': 'Error'})
                connector_source = ConnectorEnum.get_connector(source.connection.connector.id)
                controller_class = ConnectorEnum.get_controller(connector_source)
                controller = controller_class(connection=source.connection.related_connection, plug=source)
                if not controller.test_connection():
                    return JsonResponse({'data': 'Error'})
                connector_target = ConnectorEnum.get_connector(target.connection.connector.id)
                controller_class = ConnectorEnum.get_controller(connector_target)
                controller = controller_class(connection=target.connection.related_connection, plug=target)
                if not controller.test_connection():
                    return JsonResponse({'data': 'Error'})
            else:
                return JsonResponse(
                    {'data': "You don't have permission to toggle this gear."})
            try:
                # update_plug.s(g.source.id, g.id).apply_async(queue='manual-queue')
                update_plug.s(g.source.id, g.id).apply_async()
            except Exception as e:
                return JsonResponse({'data': 'Problem updating Gear - {0}.'.format(e)})
        except Gear.DoesNotExist:
            return JsonResponse({'data': 'Error invalid gear id.'})
    return JsonResponse({'data': 'request needs to be ajax'})