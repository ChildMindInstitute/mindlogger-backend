# -*- coding: utf-8 -*-
from ..rest import Resource
from ..describe import Description, autoDescribeRoute
from girderformindlogger.api import access
from girderformindlogger.models.applet_library import AppletLibrary as AppletLibraryModel
from girderformindlogger.constants import AccessType, SortDir, TokenScope,     \
    DEFINED_INFORMANTS, REPROLIB_CANONICAL, SPECIAL_SUBJECTS, USER_ROLES
from girderformindlogger.models.profile import Profile as ProfileModel
from girderformindlogger.models.applet_categories import AppletCategory
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.utility import jsonld_expander
from pymongo import DESCENDING, ASCENDING
from bson.objectid import ObjectId


USER_ROLE_KEYS = USER_ROLES.keys()

class AppletLibrary(Resource):
    """API Endpoint for managing library data in the system."""

    def __init__(self):
        super(AppletLibrary, self).__init__()
        self.resourceName = 'library'
        self._model = AppletLibraryModel()

        self.route('GET', ('applets',), self.getApplets)
        self.route('GET', ('categories',), self.getCategories)
        self.route('GET', (':id', 'checkName',), self.checkAppletName)
        self.route('GET', ('applet', 'content'), self.getPublishedApplet)

        self.route('POST', ('categories',), self.addCategory)

    @access.public
    @autoDescribeRoute(
        Description('Get Published Applets.')
        .notes(
            'Get applets published in the library.'
        )
    )
    def getApplets(self):
        libraryApplets = list(self._model.find({}))

        appletIds = []
        for libraryApplet in libraryApplets:
            appletIds.append(libraryApplet['appletId'])

        appletModel = AppletModel()

        applets = list(appletModel.find({
            '_id': {
                '$in': appletIds
            }
        }))

        appletMetaInfoById = {}
        for applet in applets:
            appletMetaInfoById[str(applet['_id'])] = appletModel.getAppletMeta(applet)

        result = []
        for libraryApplet in libraryApplets:
            result.append({
                'id': libraryApplet['_id'],
                'name': libraryApplet['name'],
                'accountId': libraryApplet['accountId'],
                'categoryId': libraryApplet['categoryId'],
                'subCategoryId': libraryApplet['subCategoryId'],
                'keywords': libraryApplet['keywords'],
                'description': appletMetaInfoById[str(libraryApplet['appletId'])].get('description', ''),
                'image': appletMetaInfoById[str(libraryApplet['appletId'])].get('image', '')
            })

        return result

    @access.public
    @autoDescribeRoute(
        Description('Get Content of an applet.')
        .notes(
            'Get Content of published applet.'
        )
        .param(
            'libraryId',
            description='ID of the applet in the library',
            required=True
        )
    )
    def getPublishedApplet(self, libraryId):
        libraryApplet = self._model.findOne({
            '_id': ObjectId(libraryId)
        })

        applet = AppletModel().findOne({
            '_id': libraryApplet['appletId']
        })

        formatted = jsonld_expander.formatLdObject(
            applet,
            'applet',
            None,
            refreshCache=False
        )

        formatted['accountId'] = libraryApplet['accountId']

        return formatted

    @access.public
    @autoDescribeRoute(
        Description('Get Applet Categories.')
        .notes(
            'Get categories/sub-categories for applets.'
        )
    )
    def getCategories(self):
        categories = list(AppletCategory().find({}, fields=['name', 'parentId']))
        return categories

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Check applet name in the Library.')
        .notes(
            'Check if there is an applet with same name already exists in the library. <br>'
        )
        .modelParam(
            'id',
            model=AppletModel,
            description='ID of the applet',
            destName='applet',
            level=AccessType.ADMIN
        )
        .param(
            'name',
            'name of applet',
            required=True
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def checkAppletName(self, applet, name):
        existing = self._model.findOne({
            'name': name,
            'appletId': {
                '$ne': applet['_id']
            }
        })

        if existing:
            return False

        return True

    @access.public
    @autoDescribeRoute(
        Description('Get Content of an applet.')
        .notes(
            'Get Content of published applet.'
        )
        .param(
            'name',
            'name of category',
            required=True
        )
        .param(
            'parentId',
            'parent category id',
            required=False,
            default=None
        )
    )
    def addCategory(self, name, parentId=None):
        return AppletCategory().addCategory(name, parentId)
