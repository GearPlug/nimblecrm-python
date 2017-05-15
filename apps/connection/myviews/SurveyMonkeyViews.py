from django.http import JsonResponse
from django.views.generic import TemplateView

from apps.gp.views import TemplateViewWithPost
from apps.gp.controllers.lead import SurveyMonkeyController
from apps.gp.models import SurveyMonkeyConnection


# Vista base de facebook. Hace request utilizando el graph api.
class AJAXGetSurveyListView(TemplateViewWithPost):
    template_name = 'wizard/async/select_options.html'
    has_objects = False
    smc = SurveyMonkeyController()

    def get_context_data(self, *args, **kwargs):
        context = super(AJAXGetSurveyListView, self).get_context_data(**kwargs)
        connection_id = self.request.POST.get('connection_id', '')
        connection = SurveyMonkeyConnection.objects.get(pk=connection_id)
        a = self.smc.create_connection(connection)
        object_list = [{'name': o['title'], 'id': o['id']} for o in self.smc.get_survey_list()]
        if object_list:
            self.has_objects = True
        context['object_list'] = object_list
        return context

