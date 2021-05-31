# -*- coding: utf-8 -*-
from ..rest import Resource
from ..describe import Description, autoDescribeRoute
from girderformindlogger.api import access
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
        self.route('GET', ('categories',), self.getCategories)
        self.route('GET', (':id', 'checkName',), self.checkAppletName)
        self.route('GET', ('applet', 'content'), self.getPublishedApplet)

        self.route('POST', ('categories',), self.addCategory)
        self.route('POST', ('basket', ), self.setBasket)
        self.route('GET', ('basket', ), self.getBasket)
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
        })

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
        })

        applet = AppletModel().findOne({
            '_id': libraryApplet['appletId']
        })

        protocolId = applet.get('meta', {}).get('protocol', {}).get('_id', '').split('/')[-1]

        items = list(ItemModel().find({
            'meta.protocolId': ObjectId(protocolId)
        }))

        updates = {}
        editors = {}

        userModel = UserModel()
        for item in items:
            if 'identifier' in item['meta'] and 'lastUpdatedBy' in item:
                editorId = str(item['lastUpdatedBy'])

                if editorId not in editors:
                    user = userModel.findOne({
                        '_id': item['lastUpdatedBy']
                    })

                    editors[editorId] = user['firstName']

                updates[item['meta']['identifier']] = {
                    'updated': item['updated'],
                    'lastUpdatedBy': editors[editorId]
                }

        return updates


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
        keys = ['name', 'keywords', 'description', 'activities.name', 'activities.items.name']
        libraryApplets = list(
            self._model.find({
                '$or': [
                    {
                        key: {
                            '$regex': f'{searchText}',
                            '$options' :'i'
                        }
                    } for key in keys
                ]
            }, fields=self._model.metaFields, sort=[("name", ASCENDING)])
        )

        totalCount = len(libraryApplets)
        libraryApplets = libraryApplets[recordsPerPage * pageIndex: recordsPerPage]

        appletIds = []
        for libraryApplet in libraryApplets:
            appletIds.append(libraryApplet['appletId'])

        appletModel = AppletModel()

        applets = list(appletModel.find({
            '_id': {
                '$in': appletIds
            }
        }))

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
    def getPublishedApplet(self, libraryId, nextActivity):
        libraryApplet = self._model.findOne({
            '_id': ObjectId(libraryId)
        })

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
        appletName = name.strip().replace("(", "\\(").replace(")", "\\)")
        existing = self._model.findOne({
            'name': {
                '$regex': f'^{appletName}$',
                '$options': 'i'
            },
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
