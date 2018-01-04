from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch, prefetch_related_objects
from django.forms import modelform_factory, modelformset_factory
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, FormView
from django.views.generic.edit import FormMixin
from django.http.response import JsonResponse, HttpResponseForbidden, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from apps.gear.apps import APP_NAME as app_name
from apps.gear.forms import MapForm, SendHistoryForm, DownloadHistoryForm, FiltersForm
from apps.gp.enum import ConnectorEnum
from apps.gp.tasks import dispatch
from apps.gp.models import Gear, Plug, StoredData, GearMap, GearMapData, GearGroup, GearFilter, Connector
from apps.history.models import DownloadHistory, SendHistory
from oauth2client import client
from django.shortcuts import render
import httplib2
import json
import datetime
from django.apps import apps
from apiconnector import settings


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
        return self.model.objects.filter(user=self.request.user).prefetch_related('gear').prefetch_related(
            'gear__source__connection__connector').prefetch_related(
            'gear__target__connection__connector').prefetch_related('gear__gear_map')


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
    success_url = reverse_lazy('%s:sucess_create' % app_name)
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

    def get_success_url(self, **kwargs):
        # async
        return super(CreateGearMapView, self).get_success_url()

    def form_valid(self, form, *args, **kwargs):
        _version = GearMapData.objects.filter(gear_map=self.gear_map).last()
        for f, v in form.cleaned_data.items():
            if _version is not None:
                if v is not None and (v != '' or not v.isspace()):
                    _final_version = _version.version + 1
                    GearMapData.objects.create(gear_map=self.gear_map, target_name=f, source_value=v,
                                               version=_final_version)
                self.gear_map.version = _final_version
                self.gear_map.save()
            elif _version is None:
                if v is not None and (v != '' or not v.isspace()):
                    GearMapData.objects.create(gear_map=self.gear_map, target_name=f, source_value=v)
            else:
                raise
        #self.gear_map.gear.is_active = True
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
            try:
                _version = GearMapData.objects.filter(gear_map=self.gear_map).order_by('-version').values('version')[0]
                all_data = GearMapData.objects.filter(gear_map=self.gear_map, version=_version['version'])
            except IndexError:
                all_data = None

            for label, field in form.fields.items():
                print(label)
                try:
                    field.initial = all_data.get(target_name=label).source_value
                except AttributeError:
                    break
                except:
                    pass
        return form

    def get_available_source_fields(self, plug):
        c = ConnectorEnum.get_connector(plug.connection.connector.id)
        if c == ConnectorEnum.GoogleContacts:
            self.google_contacts_controller.create_connection(plug.connection.related_connection, plug)
            return ['%%{0}%%'.format(field) for field in self.google_contacts_controller.get_contact_fields()]
        return [('%%{0}%%'.format(item['name']), item['value']) for item in
                StoredData.objects.filter(plug=plug, connection=plug.connection).values()]

    def get_target_field_list(self, plug):
        c = ConnectorEnum.get_connector(plug.connection.connector.id)
        controller_class = ConnectorEnum.get_controller(c)
        related = plug.connection.related_connection
        controller = controller_class(connection=related, plug=plug)
        if controller.test_connection():
            return controller.get_mapping_fields()
        return []

class GearSendHistoryView(FormMixin, LoginRequiredMixin, ListView, ):
    model = SendHistory
    form_class = SendHistoryForm
    template_name = 'gear/send_history.html'
    login_url = '/accounts/login/'
    paginate_by = 30

    def get_queryset(self, **kwargs):
        order = '-date'
        if self.request.method == "POST":
            if 'date_from' in self.request.POST and self.request.POST['date_from']:
                if 'date_to' in self.request.POST and self.request.POST['date_to']:
                    kwargs['date__range'] = (self.request.POST['date_from'], self.request.POST['date_to'])
                else:
                    kwargs['date__gte'] = self.request.POST['date_from']
            elif 'date_to' in self.request.POST and self.request.POST['date_to']:
                kwargs['date__lte'] = self.request.POST['date_to']
            if 'order' in self.request.POST and self.request.POST['order'] == 'asc':
                order = 'date'
            if 'sent' in kwargs and kwargs['sent'] == '0':
                del kwargs['sent']
            del kwargs['date_from']
            del kwargs['date_to']
            del kwargs['order']
        queryset = self.model.objects.filter(gear_id=self.kwargs['pk'], **kwargs).order_by(order)
        connector_list = Connector.objects.filter(pk__in=[i.connector_id for i in queryset.iterator()])
        if connector_list.count() > 1:
            for item in queryset:
                connector = None
                for c in connector_list:
                    if str(c.id) == item.connector_id:
                        connector = c
                        break
                setattr(item, 'connector', connector)
                setattr(item, 'parsed_data', [{'name': k, 'value': v} for k, v in json.loads(item.data).items()])
        else:
            try:
                connector = connector_list[0]
                for item in queryset:
                    setattr(item, 'parsed_data', [{'name': k, 'value': v} for k, v in json.loads(item.data).items()])
                    setattr(item, 'connector', connector)
            except IndexError:
                pass
        return queryset

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


class GearActivityHistoryView(FormMixin, LoginRequiredMixin, ListView, ):
    model = SendHistory
    form_class = SendHistoryForm
    template_name = 'gear/recent_activity.html'
    login_url = '/accounts/login/'

    def get_queryset(self, **kwargs):
        NOW = timezone.now()
        gears = Gear.objects.filter(user_id=self.request.user.id).prefetch_related(
            Prefetch('source__connection__connector'), Prefetch('target__connection__connector'))
        activity_result = []
        min_date = NOW - timezone.timedelta(hours=24)
        activity_list = self.model.objects.filter(gear_id__in=[str(g.id) for g in gears.iterator()],
                                                  date__range=(min_date, NOW)).order_by('-date')[:30]
        for activity in activity_list.iterator():
            current_gear = None
            for g in gears:
                if str(g.id) == activity.gear_id:
                    current_gear = g
                    break
            if current_gear is not None:
                a = {'id': activity.id, 'date': activity.date, 'sent': activity.sent, 'response': activity.response,
                     'identifier': activity.identifier,
                     'connection': json.loads(activity.connection)[0]['fields']['name'],
                     'connector_source': current_gear.source.connection.connector,
                     'connector_target': current_gear.target.connection.connector,
                     'data': [{'name': k, 'value': v} for k, v in json.loads(activity.data).items()], }
                activity_result.append(a)
        return activity_result

    def get(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return HttpResponseForbidden()
        except:
            return HttpResponseForbidden()
        return super(GearActivityHistoryView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(GearActivityHistoryView, self).get_context_data(**kwargs)
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
                try:
                    if g.gear_map.is_active is True:
                        g.is_active = not g.is_active
                        g.save(update_fields=['is_active', ])
                    else:
                        return JsonResponse({'data': 'There\'s no active gear map.'})
                except:
                    return JsonResponse({'data': 'There\'s no active gear map.'})
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
                controller_s = controller_class(connection=source.connection.related_connection, plug=source)
                if not controller_s.test_connection():
                    return JsonResponse({'data': 'Error. Source is inactive.'})
                connector_target = ConnectorEnum.get_connector(target.connection.connector.id)
                controller_class = ConnectorEnum.get_controller(connector_target)
                controller_t = controller_class(connection=target.connection.related_connection, plug=target)
                if not controller_t.test_connection():
                    return JsonResponse({'data': 'Error. Target is inactive.'})
            else:
                return JsonResponse(
                    {'data': "You don't have permission to toggle this gear."})
            try:
                dispatch.s(g.id).apply_async(queue='dispatch')
                # dispatch.s(g.id).apply_async()
                pass
            except Exception as e:
                return JsonResponse({'data': 'Problem updating Gear - {0}.'.format(e)})
        except Gear.DoesNotExist:
            return JsonResponse({'data': 'Error invalid gear id.'})
    return JsonResponse({'data': 'request needs to be ajax'})





