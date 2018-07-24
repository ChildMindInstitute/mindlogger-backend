[![CircleCI](https://circleci.com/gh/ChildMindInstitute/mindlogger-app-backend/tree/circleci.svg?style=svg)](https://circleci.com/gh/ChildMindInstitute/mindlogger-app-backend/tree/circleci) [![Python coverage](.circleci/python-coverage.svg)](https://circleci.com/gh/ChildMindInstitute/mindlogger-app-backend/tree/circleci)
[![ReadTheDocs](https://readthedocs.org/projects/mindlogger-app-backend/badge/?version=girder-dev)](https://mindlogger-app-backend.readthedocs.io/en/girder-dev/?badge=girder-dev)

# App_ModularDataCollection_Backend
This backend serves as an administration console for customizing and storing data from the modular data collection app.

---
# Girder Structure

- [Collections](#collections)
	- [Volumes](#volumes)
		- [Activities](#activities)
			- [[Activity]](#activity)
				- [[Version]](#version)
  				- [meta.abbreviation](#metaabbreviation)
  				- [meta.accordion](#metaaccordion)
  				- [meta.@context](#metacontext)
  				- [meta.pav:createdBy](#metapavcreatedby)
    				- [@id](#id)
  				- [[File]](#file)
  				- [meta.pav:lastUpdatedOn](#metapavlastupdatedon)
  				- [meta.oslc:modifiedBy](#metaoslcmodifiedby)
    				- [@id](#id-1)
  				- [meta.schema:name](#metaschemaname)
  				- [meta.respondent](#metarespondent)
  				- [[Screen]](#screen)
    				- [meta.@context](#metacontext-1)
    				- [meta.schema:name](#metaschemaname-1)
    				- [meta.options](#metaoptions)
      			    	- [[option]](#-option)
    				- [meta.question_image](#metaquestionimage)
    				  - [@id](#-id)
    				- [meta.question_text](#metaquestiontext)
    				- [meta.response_type](#metaresponsetype)
  				- [meta.screens](#metascreens)
  				  - [@id](#id-2)
  				- [meta.status](#metastatus)
		- [Schedules](#schedules)
			- [[Frequency]](#frequency)
				- [meta.activities](#metaactivities)
  			    	- [@id](#id-3)
  			    	- [name](#name)
				- [meta.@context](#metacontext-2)
- [Groups](#groups)
	- [Editors](#editors)
	- [Managers](#managers)
	- [Users](#users)
	- [Viewers](#viewers)
- [Users](#users-1)
	- [[Volume]](#volume)
		- [Responses](#responses)
			- [[Activity]](#activity-1)
				- [[Version]](#version-1)
  			    	- [[Completed Activity]](#completed-activity)
		- [Schedules](#schedules-1)
			- [[Schedule]](#schedule)
				- [activities](#activities-1)
    				- [@id](#id-4)
    				- [name](#name-1)

## Collections

### Volumes

The **Volumes** Collection includes a Folder for each Mindlogger **Volume**.

#### Activities

Each [**Volume**].**Activities** Folder is organized into a Folder for each [**Activity**].

##### [Activity]

Each [**Volume**].**Activities**.[**Activity**] Folder contains an Item for each [**Version**] of that [**Activity**].

###### [Version]
Each **Activities**.[**Activity**].[**Version**] Folder contains JSON-LD metadata.

###### *meta.abbreviation*

String abbreviation for this [**Activity**].[**Version**] (not necessarily unique).

###### *meta.accordion*

Boolean, display this [**Activity**].[**Version**]'s **Screens** in an accordion format instead of a discrete series of screens?

###### *meta.@context*

JSON-LD object with prefix and type definitions.

###### *meta.pav:createdBy*

A JSON-LD object with an **@id** key and a value that resolves to the Mindlogger User who created this [**Activity**].[**Version**].

###### _**@id**_

String in the format "user/[girder_id]".

###### *[File]*

An Audio File, Image File or Video File to be presented on a [**Screen**] in this [**Activity**].[**Version**].

###### *meta.pav:lastUpdatedOn*

Datetime of last update.

###### *meta.oslc:modifiedBy*

Array of JSON-LD objects that resolves to Mindlogger Users who have ever modified this [**Activity**].[**Version**].

###### __*@id*__

String in the format "user/[girder_id]".

###### *meta.schema:name*

JSON-LD object with **@language** and **@value** strings.

###### *meta.respondent*

String (for now) indicating the intended respondent in relationship to the target individual (eg, "Self", "Parent", "Teacher", "Peer").

###### *[Screen]*

Each [**Screen**] Item contains JSON-LD metadata, including **@context**, **schema:name**, **options**, **question_image**, **question_text**, **response_type** and any relevant media (images, audio, and/or video files).

###### *__meta.@context__*

JSON-LD object with prefix and type definitions.


###### *__meta.schema:name__*

JSON-LD object with **@language** and **@value** strings.

###### *__meta.options__*

JSON-LD array of objects (ordered).

###### - [option]

Each [**Screen**].**meta.options**.[**option**] contains a stimulus to be presented to the **User** (eg, an **option_text** object JSON-LD object with **@language** and **@value** strings) and a **value** string to be stored / used for scoring if that response **[option]** is chosen.

###### *__meta.question_image__*
A JSON-LD object that resolves to an Image URL through the Mindlogger Girder API.

###### - @id
A string in the format "file/[girder_id]".

###### *__meta.question_text__*

JSON-LD object with **@language** and **@value** strings.

###### *__meta.response_type__*

String (for now).

###### *meta.screens*

JSON-LD array (ordered) of **Screens** to display, in sequence, for this [**Activity**].[**Version**]. This sequence is the default order that will be presented if the **User** chooses "Skip" on every **Screen**.

###### __*@id*__

Each object in a **meta.screens** array contains an **@id** key with a string value that resolves to a Mindlogger **Screen** in the Girder API.

###### *meta.status*

String (for now): "active" or "inactive".

#### Schedules

Each [**Volume**] Folder can contain a **Schedules** Folder organized into [**Frequency**] Folders.

##### [Frequency]

Each [**Frequency**] Folder contains assignable [**Assignment**] Items.

###### *meta.activities*

A JSON-LD array (ordered by priority) of **Activities** to be completed with the parent **Frequency**.

###### *__@id__*
A string in the format "item/[girder_id]"

###### *__name__*
A string to show in the **User**'s app for this **Schedule**.

###### *meta.@context*

JSON-LD object with prefix and type definitions.

## Users

**User** objects contain [**Volume**] Folders.

### [Volume]

[**Volume**] Folders contain **Schedules** Folders [of **Activities**] and **Responses** Folders [of that User's previously completed **Activities**].

#### Responses

[**User**].[**Volume**].**Responses** Folders each contain a Folder for each **Activity** the parent **User** has completed in that **Volume**.

##### [Activity]

Each [**User**].[**Volume**].**Responses**.[**Activity**] Folder contains a Folder for each version of that **Activity** the **User** has completed.

###### [Version]
Each [**User**].[**Volume**].**Responses**.[**Activity**].[**Version**] Folder contains an Item for each **Completed Activity** instance for that relative (**User** + **Activity**.**Version**) combination.

###### *[Completed Activity]*
Each [**User**].[**Volume**].**Responses**.[**Activity**].[**Version**].**Completed Activity** Item contains JSON-LD metadata, including context, os, and responses.

#### Schedules

Each [**User**].[**Volume**].**Schedules** Folder contains a **Schedule** Item for each **Volume**.

##### [Schedule]

Each [**User**].[**Volume**].**Schedules**.[**Schedule**] contains JSON-LD metadata, including context and an array of **Activity** objects.

###### activities

Each object in a [**User**].[**Volume**].**Schedules**.[**Schedule**].activities array includes an **@id** and a **name**.

###### *@id*
A string in the format "item/[girder_id]"

###### *name*
A string to show in the **User**'s app for this **Schedule**.

## Groups

### Editors

**Editors** can create **Screens**, **Activities** and **Schedules**.

### Managers

**Managers** can assign **Viewers** and **Activities** to **Users**.

### Users

**Users** can perform **Activities** assigned to them by **Managers**.

### Viewers

**Viewers** can view data from **Users** as assigned by **Managers**.
