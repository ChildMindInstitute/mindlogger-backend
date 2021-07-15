#!/usr/bin/env python
# -*- coding: utf-8 -*-

# themes are used to apply an organisations color, logo etc. to an applets

###############################################################################
#  Copyright 2013 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

from ..describe import Description, autoDescribeRoute
from ..rest import Resource
from girderformindlogger.utility.validate import isValidImageUrl, isValidHexColor
from girderformindlogger.api import access
from girderformindlogger.constants import TokenScope
from girderformindlogger.exceptions import AccessException, ValidationException

from girderformindlogger.models.user import User as UserModel
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.collection import Collection

from bson.objectid import ObjectId


def findThemeById(themeId=None):
    """use the theme id to look up the logo, colors etc. for a theme.
    if themeId or a theme is not found, returns None""" 
    if themeId==None:
        return None

    theme = FolderModel().findOne({"_id":ObjectId(str(themeId))})
    
    if theme==None:
        return None

    else:
        return theme.get('meta')


def validateThemeColor(color, fieldName=None):
    """"
    check that the theme color matches a 6 charater hex code.
    returns True or raises a ValidationException
    """
    if not isValidHexColor(color):
        raise ValidationException(
            f"{fieldName} is not a valid hex color. Provided colors must be valid hexadecimal, start with '#' and contain 6 characters e.g.: #09AFaf")

    return True


def validateTheme(name=None,
                logo=None,
                backgroundImage=None,
                primaryColor=None,
                secondaryColor=None,
                tertiaryColor=None):
    """"
    check that provided inputs to a theme definition pass validation checks or are None
    returns True or raises ValidationException
    """
    
    if logo:
        if not isValidImageUrl(logo):
            raise ValidationException("logo url is not a valid url. example valid url: https://sitename.com/image.png")

    if backgroundImage:
        if not isValidImageUrl(backgroundImage):
            raise ValidationException("backgroundImage url is not a valid url. example valid url: https://sitename.com/image.png")

    if primaryColor:
        validateThemeColor(color=primaryColor, fieldName="primaryColor")

    if secondaryColor:
        validateThemeColor(color=secondaryColor, fieldName="secondaryColor")

    if tertiaryColor:
        validateThemeColor(color=tertiaryColor, fieldName="tertiaryColor")

    return True



class Theme(Resource):
    """API Endpoint for themes."""

    def __init__(self):
        super().__init__()
        self.resourceName = 'theme'
        self.route('POST', (), self.createTheme)
        self.route('GET', (), self.readTheme)
        self.route('PUT', (':id',), self.updateTheme)
        self.route('DELETE', (':id',), self.deleteTheme)

    def findThemeCollection(self):
        """returns the theme collection,
        creates the collection if it doesn't already exists
        """

        themeCollection = Collection().findOne({"name": "Themes"})

        # create the theme collection if it isn't there
        if not themeCollection:
            Collection().createCollection('Themes')
            themeCollection = Collection().findOne({"name": "Themes"})

        return themeCollection


    def updateThemeFolder(
        self,
        theme,
        themeSettings
        ):
        """
        save updates to the meta field of a theme folder. 
        query the db to return the updated document 
        """

        theme['meta'].update(themeSettings)        
        FolderModel().save(theme, validate=False)
        theme = FolderModel().findOne({'_id': ObjectId(theme['_id'])})

        return theme


    # @access.admin(scope=TokenScope.DATA_WRITE)
    @access.public
    @autoDescribeRoute(
        Description('Create a new theme.')
        .notes(
            'This endpoint is used to define a theme that can be used to reskin/style an applet. <br>'
        )
        .errorResponse()
        .param(
            'name',
            'Set the name of the theme. Usually the name of an institution e.g.: CMI. will raise an exception if the name already exists',
            dataType='string',
            required=True
        )
        .param(
            'logo',
            'a url of a logo of the institution creating the applet',
            dataType='string',
            required=False
        )
        .param(
            'backgroundImage',
            'url of an image to be displayed in the background of the applet',
            dataType='string',
            required=False
        )
        .param(
            'primaryColor',
            'set the main color for styling the applet. Used for header, footer, navbar and buttons',
            dataType='string',
            required=False
        )
        .param(
            'secondaryColor',
            'Set a secondary color',
            dataType='string',
            required=False
        )
        .param(
            'tertiaryColor',
            'Set a tertiary color',
            dataType='string',
            required=False
        )
    )
    def createTheme(self,
        name=None,
        logo=None,
        backgroundImage=None,
        primaryColor=None,
        secondaryColor=None,
        tertiaryColor=None,
        ):
        """
        Create a theme
        """
        user = self.getCurrentUser()
        #### TO DO -> require admin permission to create Theme
        # if user is not an admin :
        #     raise AccessException("You must be an administrator to create a Theme.")

        themeCollection = self.findThemeCollection()

        validateTheme(name=name,
                logo=logo,
                backgroundImage=backgroundImage,
                primaryColor=primaryColor,
                secondaryColor=secondaryColor,
                tertiaryColor=tertiaryColor)

        newTheme = FolderModel().createFolder(
                        parent=themeCollection,
                        name=name,
                        parentType='collection',
                        public=True,
                        creator=user,
                        allowRename=False)

        themeSettings =  {
            "name":newTheme['name'],
            "logo":logo,
            "backgroundImage": backgroundImage,
            "primaryColor":primaryColor,
            "secondaryColor":secondaryColor,
            "tertiaryColor":tertiaryColor
        }

        newTheme = self.updateThemeFolder(newTheme, themeSettings)

        return newTheme


    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Get a theme by ID, name or return all.')
        .notes(
            'This endpoint is used to get a theme by name or id, or get all themes. <br>'
        )
        .param(
            'id',
            'ID of the theme',
            required=False
        )
        .param(
            'name',
            'name of the theme',
            required=False
        )
        .errorResponse()
    )
    def readTheme(self, id=None, name=None):
        """
        Get a theme as a json document.
        """

        if name: 
            theme = FolderModel().findOne({"name":str(name)})
            if theme==None:
                raise ValidationException(f"theme not found for id: {id}")
            response = theme['meta']
            response['_id'] = theme['_id']
            return response

        if id:
            theme = FolderModel().findOne({"_id":ObjectId(str(id))})
            if theme==None:
                raise ValidationException(f"theme not found for id: {id}")
            response = theme['meta']
            response['_id'] = theme['_id']
            return response

        else:
            themeCollection = self.findThemeCollection()
            parentId = str(themeCollection["_id"])
            query = {"parentId" : ObjectId(parentId)}
            themes = FolderModel().find(query)

            # get the paramaters for the theme and insert the theme id number
            response = []
            for theme in themes:
                themeSettings = theme["meta"]
                if themeSettings != {}:
                    themeSettings["_id"] = theme["_id"]
                    response.append(themeSettings)
            
            return response


    # @access.admin(scope=TokenScope.DATA_WRITE)
    @access.public
    @autoDescribeRoute(
        Description('Update an existing theme.')
        .notes(
            'This endpoint is used to update a theme that can be used to reskin/style an applet. <br>'
        )
        .errorResponse()
        .param(
            'id',
            'the id of the theme',
            required=True
        )
        .param(
            'name',
            'Set the name of the theme. Usually the name of an institution e.g.: CMI',
            dataType='string',
            required=False
        )
        .param(
            'logo',
            'a url of a logo of the institution creating the applet',
            dataType='string',
            required=False
        )
        .param(
            'backgroundImage',
            'url of an image to be displayed in the background of the applet',
            dataType='string',
            required=False
        )
        .param(
            'primaryColor',
            'set the main color for styling the applet. Used for header, footer, navbar and buttons',
            dataType='string',
            required=False
        )
        .param(
            'secondaryColor',
            'Set a secondary color',
            dataType='string',
            required=False
        )
        .param(
            'tertiaryColor',
            'Set a tertiary color',
            dataType='string',
            required=False
        )
    )
    def updateTheme(self,
        id,
        name=None,
        logo=None,
        backgroundImage=None,
        primaryColor=None,
        secondaryColor=None,
        tertiaryColor=None,
        ):
        """
        endpoint for updating a theme
        """        
        #get existing theme document
        theme = FolderModel().findOne({"_id":ObjectId(str(id))})

        if theme==None:
            raise ValidationException(f"theme not found for id: {id}")
        
        validateTheme(name=name,
                      logo=logo,
                      backgroundImage=backgroundImage,
                      primaryColor=primaryColor,
                      secondaryColor=secondaryColor,
                      tertiaryColor=tertiaryColor)

        #  update the folder's name field (outside of the metadata object)
        if name:
            theme['name'] = name
            FolderModel().save(theme)

        newThemeSettings =  {
            "name":name,
            "logo":logo,
            "backgroundImage": backgroundImage,
            "primaryColor":primaryColor,
            "secondaryColor":secondaryColor,
            "tertiaryColor":tertiaryColor
        }

        #filter out parameters that were not passed and update metadata
        newThemeSettings = {k:v for k,v in newThemeSettings.items() if v != None}
        updatedTheme = self.updateThemeFolder(theme, newThemeSettings)

        return updatedTheme


    # @access.admin
    @access.public
    @autoDescribeRoute(
        Description('delete a theme by ID.')
        .notes(
            'This endpoint is used to delete a theme by id. <br>'
        )
        .param(
            'id',
            'ID of the theme',
            required=True
        )
        .errorResponse()
    )
    def deleteTheme(self, id):
        """
        delete a theme by ID.
        """

        theme = FolderModel().findOne({"_id":ObjectId(str(id))})
        if theme==None:
            raise ValidationException(f"theme not found for id: {id}")

        else:
            FolderModel().remove(theme)
            return {'message': f"Deleted theme '{theme['name']}'"}