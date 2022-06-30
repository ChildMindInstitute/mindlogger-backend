# -*- coding: utf-8 -*-
from ..rest import Resource
from ..describe import Description, autoDescribeRoute
from girderformindlogger.api import access
from girderformindlogger.exceptions import AccessException, ValidationException
from girderformindlogger.models.applet_library import AppletLibrary as AppletLibraryModel
from girderformindlogger.constants import AccessType, SortDir, TokenScope,     \
    DEFINED_INFORMANTS, REPROLIB_CANONICAL, SPECIAL_SUBJECTS, USER_ROLES, MAX_PULL_SIZE
from girderformindlogger.models.profile import Profile as ProfileModel
from girderformindlogger.models.applet_categories import AppletCategory
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.models.activity import Activity as ActivityModel
from girderformindlogger.models.applet_basket import AppletBasket
from girderformindlogger.utility import jsonld_expander
from pymongo import DESCENDING, ASCENDING
from bson.objectid import ObjectId
from girderformindlogger.models.protocol import Protocol as ProtocolModel
from girderformindlogger.models.item import Item as ItemModel

USER_ROLE_KEYS = USER_ROLES.keys()

class AppletLibrary(Resource):
    """API Endpoint for managing library data in the system."""

    def __init__(self):
        super(AppletLibrary, self).__init__()
        self.resourceName = 'library'
        self._model = AppletLibraryModel()

        self.route('GET', ('applets',), self.getApplets)
        self.route('GET', ('applet',), self.getApplet)
        self.route('GET', ('categories',), self.getCategories)
        self.route('GET', (':id', 'checkName',), self.checkAppletName)
        self.route('GET', ('applet', 'content'), self.getPublishedContent)

        self.route('POST', ('categories',), self.addCategory)
        self.route('POST', ('basket', ), self.setBasket)
        self.route('GET', ('basket', ), self.getBasket)
        self.route('PUT', ('basket', 'applets',), self.getAppletsForBasket)
        self.route('GET', ('basket', 'content',), self.getBasketContent)
        self.route('PUT', ('basket', 'selection'), self.updateBasket)
        self.route('DELETE', ('basket', 'applet'), self.deleteAppletFromBasket)

        self.route('GET', ('contribution', 'origin'), self.getProtocolContributions)
        self.route('GET', ('contribution', 'updates'), self.getProtocolUpdates)

    @access.public
    @autoDescribeRoute(
        Description('Get content of protocol by applet id.')
        .param(
            'libraryId',
            description='ID of the applet in the library',
            required=True
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Read access was denied for this applet.', 403)
    )
    def getProtocolContributions(self, libraryId):
        libraryApplet = self._model.findOne({
            '_id': ObjectId(libraryId)
        }, fields=self._model.metaFields)

        applet = AppletModel().findOne({
            '_id': libraryApplet['appletId']
        })

        protocolId = applet.get('meta', {}).get('protocol', {}).get('_id', '').split('/')[-1]

        return ProtocolModel().getContributions(protocolId)

    @access.public
    @autoDescribeRoute(
        Description('Get content of protocol by applet id.')
        .param(
            'libraryId',
            description='ID of the applet in the library',
            required=True
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Read access was denied for this applet.', 403)
    )
    def getProtocolUpdates(self, libraryId):
        libraryApplet = self._model.findOne({
            '_id': ObjectId(libraryId)
        }, fields=self._model.metaFields)

        applet = AppletModel().findOne({
            '_id': libraryApplet['appletId']
        })

        protocolId = applet.get('meta', {}).get('protocol', {}).get('_id', '').split('/')[-1]

        return ProtocolModel().getProtocolUpdates(protocolId)

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Set Basket.')
        .notes(
            'This endpoint is used after user logs in applet library. ( items added to based on logged out state are sent for initialization. )'
        )
        .jsonParam(
            'basket',
            'a json object specifying initial basket data',
            paramType='form',
            required=True
        )
    )
    def setBasket(self, basket):
        user = self.getCurrentUser()

        AppletBasket().setSelection(user['_id'], basket)

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Get Basket.')
        .notes(
            'This endpoint is used for getting current basket for user'
        )
    )
    def getBasket(self):
        user = self.getCurrentUser()

        return AppletBasket().getBasket(user['_id'])

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Get Content applets in Basket.')
        .notes(
            'This endpoint is used for getting content of basket for user'
        )
    )
    def getBasketContent(self):
        result = {}

        user = self.getCurrentUser()
        basket = AppletBasket().getBasket(user['_id'])

        appletModel = AppletModel()
        activityModel = ActivityModel()

        for appletId in basket:
            selection = basket[appletId]

            applet = appletModel.findOne({
                '_id': ObjectId(appletId)
            })

            formatted = jsonld_expander.formatLdObject(
                applet,
                'applet',
                None,
                refreshCache=False
            )

            formatted['accountId'] = applet['accountId']

            if selection is None: # select whole applet
                result[appletId] = appletModel.getNextAppletData(formatted['activities'], None, MAX_PULL_SIZE)
            else:
                activityIDToIRI = {}
                itemIDToIRI = {}

                content = formatted.copy()
                content['activities'] = {}
                content['items'] = {}

                for activityIRI in formatted['activities']:
                    activityIDToIRI[str(formatted['activities'][activityIRI])] = activityIRI

                for activitySelection in selection:
                    activityId = activitySelection['activityId']
                    items = activitySelection.get('items', None)

                    activityIRI = activityIDToIRI[str(activityId)]

                    activity = activityModel.findOne({
                        '_id': ObjectId(activityId)
                    })

                    formattedActivity = jsonld_expander.formatLdObject(
                        activity,
                        'activity'
                    )

                    content['activities'][activityIRI] = formattedActivity['activity']

                    if items: # select specific items
                        itemIDToIRI = {}
                        content['activities'][activityIRI] = activityModel.disableConditionals(formattedActivity['activity'])
                        content['activities'][activityIRI] = activityModel.disableCumulatives(content['activities'][activityIRI])

                        for itemIRI in formattedActivity['items']:
                            itemID = formattedActivity['items'][itemIRI]['_id'].split('/')[-1]
                            itemIDToIRI[itemID] = itemIRI

                        for itemId in items:
                            itemIRI = itemIDToIRI.get(str(itemId), None)

                            if not itemIRI:
                                continue

                            content['items'][itemIRI] = formattedActivity['items'][itemIRI]
                    else: # select whole activity
                        for itemIRI in formattedActivity['items']:
                            content['items'][itemIRI] = formattedActivity['items'][itemIRI]

                result[appletId] = content

        return result

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Get applets used in basket.')
        .notes(
            'This endpoint is used for getting all applets used in basket'
        )
        .jsonParam(
            'basket',
            'json data containing basket selection',
            required=False,
            default=None
        )
    )
    def getAppletsForBasket(self, basket):
        user = self.getCurrentUser()

        if not basket:
            basket = AppletBasket().getBasket(user['_id'])

        appletIds = []
        for appletId in basket:
            appletIds.append(ObjectId(appletId))

        libraryApplets = list(
            self._model.find({
                'appletId': {
                    '$in': appletIds
                }
            }, fields=self._model.metaFields)
        )

        def getSortKey(applet):
            return applet['name'].lower()
        libraryApplets.sort(key=getSortKey)

        data = []
        for libraryApplet in libraryApplets:
            data.append({
                'id': libraryApplet['_id'],
                'appletId': libraryApplet['appletId'],
                'name': libraryApplet['name'],
                'accountId': libraryApplet['accountId'],
                'categoryId': libraryApplet['categoryId'],
                'subCategoryId': libraryApplet['subCategoryId'],
                'keywords': libraryApplet['keywords'],
                'description': libraryApplet.get('description'),
                'image': libraryApplet.get('image')
            })

        return data

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Update applet/activity/item selection.')
        .notes(
            'This endpoint is used when user adds new item in the basket or update selection on applet.'
        )
        .param(
            'appletId',
            'id of applet that selection is updated',
            required=True
        )
        .jsonParam(
            'selection',
            'A JSON Object containing information about basket update.',
            paramType='form',
            required=False,
            default=None
        )
    )
    def updateBasket(self, appletId, selection=None):
        user = self.getCurrentUser()

        AppletBasket().updateSelection(
            user['_id'],
            ObjectId(appletId),
            selection
        )

        return {
            'message': 'updated'
        }

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Delete a selection from basket.')
        .notes(
            'This endpoint is used for deleting a selection (applet) from basket.'
        )
        .param(
            'appletId',
            'id of applet that selection is going to be removed.',
            required=True
        )
    )
    def deleteAppletFromBasket(self, appletId):
        user = self.getCurrentUser()

        AppletBasket().deleteSelection(user['_id'], ObjectId(appletId))
        return {
            'message': 'deleted'
        }

    @access.public
    @autoDescribeRoute(
        Description('Get Published Applets.')
        .notes(
            'Get applets published in the library.'
        )
        .param(
            'recordsPerPage',
            'records per page',
            required=False,
            dataType='integer',
            default=5
        )
        .param(
            'pageIndex',
            'page index',
            dataType='integer',
            required=False,
            default=0
        )
        .param(
            'searchText',
            'search text',
            required=False,
            default=''
        )
    )
    def getApplets(self, recordsPerPage, pageIndex, searchText):
        keys = ['keywords', 'name', 'description', 'activities.name', 'activities.items.name']
        libraryApplets = []
        totalCount = 0

        def getSortKey(applet):
            return applet['name'].lower()

        appletIds = {}

        for key in keys:
            query = {
                key: { '$regex': f'{searchText}', '$options' :'i' }
            }

            if key == 'keywords':
                searchWords = searchText.split(', ')

                query = {
                    '$and': [
                        {
                            key: { '$regex': f'{word}', '$options': 'i' }
                        } for word in searchWords
                    ]
                }

            applets = list(self._model.find(query, fields=self._model.metaFields))

            applets.sort(key=getSortKey)
            for libraryApplet in applets:
                appletId = str(libraryApplet['appletId'])

                if appletId not in appletIds:
                    appletIds[appletId] = True
                    libraryApplets.append(libraryApplet)

        totalCount = len(libraryApplets)

        libraryApplets = libraryApplets[recordsPerPage * pageIndex: recordsPerPage * pageIndex + recordsPerPage]

        data = []
        for libraryApplet in libraryApplets:
            data.append({
                'id': libraryApplet['_id'],
                'appletId': libraryApplet['appletId'],
                'name': libraryApplet['name'],
                'accountId': libraryApplet['accountId'],
                'categoryId': libraryApplet['categoryId'],
                'subCategoryId': libraryApplet['subCategoryId'],
                'keywords': libraryApplet['keywords'],
                'description': libraryApplet.get('description'),
                'image': libraryApplet.get('image')
            })

        return {
            'totalCount': totalCount,
            'data': data
        }

    @access.public
    @autoDescribeRoute(
        Description('Get Published Applet.')
        .notes(
            'Get an applet published in the library.'
        )
        .param(
            'libraryId',
            description='ID of the applet in the library',
            required=True
        )
    )
    def getApplet(self, libraryId):
        libraryApplet = self._model.findOne({
            '_id': ObjectId(libraryId)
        }, fields=self._model.metaFields)

        if not libraryApplet:
            raise ValidationException('invalid applet')

        return {
            'id': libraryApplet['_id'],
            'appletId': libraryApplet['appletId'],
            'name': libraryApplet['name'],
            'accountId': libraryApplet['accountId'],
            'categoryId': libraryApplet['categoryId'],
            'subCategoryId': libraryApplet['subCategoryId'],
            'keywords': libraryApplet['keywords'],
            'description': libraryApplet.get('description'),
            'image': libraryApplet.get('image')
        }

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
        .param(
            'nextActivity',
            'id of next activity',
            default=None,
            required=False,
        )
    )
    def getPublishedContent(self, libraryId, nextActivity):
        libraryApplet = self._model.findOne({
            '_id': ObjectId(libraryId)
        }, fields=self._model.metaFields)

        if not libraryApplet:
            raise ValidationException('invalid applet')

        appletModel = AppletModel()
        applet = appletModel.findOne({
            '_id': libraryApplet['appletId']
        })

        formatted = jsonld_expander.formatLdObject(
            applet,
            'applet',
            None,
            refreshCache=False
        )

        (nextIRI, data, remaining) = appletModel.getNextAppletData(formatted['activities'], nextActivity, MAX_PULL_SIZE)

        if nextActivity:
            return {
                'nextActivity': nextIRI,
                **data
            }

        formatted['accountId'] = libraryApplet['accountId']
        formatted.update(data)

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
        words = name.strip().split(' ')

        appletName = ''
        for word in words:
            if not word:
                continue

            if len(appletName):
                appletName += ' +'

            appletName += word

        appletName = appletName.replace("(", "\\(").replace(")", "\\)")
        existing = self._model.findOne({
            'name': {
                '$regex': f'^{appletName}$',
                '$options': 'i'
            },
            'appletId': {
                '$ne': applet['_id']
            }
        }, fields=self._model.metaFields)

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
