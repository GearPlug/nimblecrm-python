from django.conf.urls import url
<<<<<<< HEAD
from apps.wizard.views import CreateGearView, CreatePlugView, CreateConnectionView, TestPlugView, \
    ActionSpecificationsView, CreateGearMapView, ListConnectorView, ListConnectionView, ActionListView, MSSQLFieldList, \
    ListGearView, GoogleDriveSheetList, GoogleSheetsWorksheetList, SugarCRMModuleList, MySQLFieldList, UpdateGearView, \
    PostgreSQLFieldList, FacebookPageList, FacebookFormList, MailChimpListsList
=======
from apps.wizard.views import CreateGearView, UpdateGearView, CreatePlugView, CreateConnectionView, \
    UpdatePlugSetActionView, CreateGearMapView, CreatePlugSpecificationView, async_spreadsheet_info, \
    async_spreadsheet_values, ListConnectorView, ListConnectionView
>>>>>>> master

urlpatterns = [
    url(r'^gear/create/$', CreateGearView.as_view(), name='create_gear'),
    url(r'^gear/list/$', CreateGearView.as_view(), name='list_gear'),
    url(r'^gear/set/plugs/(?P<pk>\d+)/$', UpdateGearView.as_view(), name='set_gear_plugs'),
    url(r'^plug/create/(?P<plug_type>(source|target)+)/$', CreatePlugView.as_view(), name='create_plug'),
    url(r'^plug/(?P<pk>\d+)/(?P<plug_type>(source|target)+)/set/action/$', UpdatePlugSetActionView.as_view(),
        name='plug_set_action'),
    url(r'^plug/(?P<plug_id>\d+)/set/specifications/$', CreatePlugSpecificationView.as_view(),
        name='plug_set_specifications'),
    url(r'connection/create/(?P<connector_id>\d+)/$', CreateConnectionView.as_view(), name='create_connection'),
    url(r'gear/map/(?P<gear_id>\d+)/$', CreateGearMapView.as_view(), name='create_gear_map'),

    url(r"^async/spreadsheet/info/(?P<plug_id>.+)/(?P<spreadsheet_id>.+)/$", async_spreadsheet_info,
        name="async_test2"),
    url(r"^async/spreadsheet/values/(?P<spreadsheet_id>.+)/(?P<worksheet_id>.+)/$", async_spreadsheet_values,
        name="async_test2"),

    # Nuevos
    url(r'^gear/update/(?P<pk>\d+)/$', UpdateGearView.as_view(), name='gear_update'),
    url(r'^connector/list/(?P<type>(source|target)+)/$', ListConnectorView.as_view(), name='connector_list'),
    url(r'^connection/list/(?P<connector_id>\d+)/(?P<type>(source|target)+)/$', ListConnectionView.as_view(),
        name='connection_list'),
<<<<<<< HEAD
    url(r'^plug/create/(?P<plug_type>(source|target)+)/$', CreatePlugView.as_view(), name='plug_create'),
    url('^plug/test/(?P<pk>\d+)/$', TestPlugView.as_view(), name='plug_test'),
    url(r'^plug/action/list/$', ActionListView.as_view(), name='action_list'),
    url(r'^plug/action/(?P<pk>\d+)/specifications/$', ActionSpecificationsView.as_view(), name='action_specifications'),
    # PLUG CREATION ASYNC
    # GoogleSheets
    url(r"async/google/drive/sheets/list/", GoogleDriveSheetList.as_view(), name='async_google_drive_sheets'),
    url(r"async/google/sheet/worksheets/", GoogleSheetsWorksheetList.as_view(), name='async_google_sheet_worksheets'),
    # SugarCRM
    url(r"async/sugarcrm/module/list/", SugarCRMModuleList.as_view(), name='async_sugarcrm_modules'),
    # MySQL
    url(r"async/mysql/field/list/", MySQLFieldList.as_view(), name='async_mysql_fields'),
    url(r"async/mssql/field/list/", MSSQLFieldList.as_view(), name='async_mssql_fields'),
    # PostgreSQL
    url(r"async/postgresql/field/list/", PostgreSQLFieldList.as_view(), name='async_postgresql_fields'),
    # Facebook
    url(r"async/facebook/page/list/", FacebookPageList.as_view(), name='async_facebook_pages'),
    url(r"async/facebook/form/list/", FacebookFormList.as_view(), name='async_facebook_forms'),
    # MailChimp
    url(r'async/mailchimp/lists/list/', MailChimpListsList.as_view(), name='async_mailchimp_lists')
=======
    # url(r'^plug/create/(?P<type>(source|target)+)/$', '', name='plug_create'),

>>>>>>> master
]
