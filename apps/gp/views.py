from django.views.generic import TemplateView


# Template sin form que acepta post
class TemplateViewWithPost(TemplateView):
    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        return super(TemplateView, self).render_to_response(context)
