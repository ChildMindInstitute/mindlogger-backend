from girderformindlogger.models.folder import Folder as FolderModel
from bson.objectid import ObjectId
from girderformindlogger.exceptions import AccessException, ValidationException
from girderformindlogger.utility.validate import isValidImageUrl, isValidHexColor

def findThemeById(themeId=None):
    """use the theme id to look up the logo, colors etc. for a theme.
    if themeId or a theme is not found, returns None"""
    if str(themeId)=='None':
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
