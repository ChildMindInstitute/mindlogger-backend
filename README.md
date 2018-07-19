[![CircleCI](https://circleci.com/gh/ChildMindInstitute/mindlogger-app-backend/tree/mongo.svg?style=svg)](https://circleci.com/gh/ChildMindInstitute/mindlogger-app-backend/tree/mongo) [![Python coverage](.circleci/python-coverage.svg)](https://circleci.com/gh/ChildMindInstitute/mindlogger-app-backend/tree/mongo)
[![ReadTheDocs](https://readthedocs.org/projects/mindlogger-app-backend/badge/?version=girder-dev)](https://mindlogger-app-backend.readthedocs.io/en/girder-dev/?badge=girder-dev)

# App_ModularDataCollection_Backend
This backend serves as an administration console for customizing and storing data from the modular data collection app.

---
# Girder Structure

- [Collections](#collections)
	- [Activities](#activities)
		- [[Activity]](#activity)
			- [[Version]](#version)
				- [meta.abbreviation](#metaabbreviation)
				- [meta.accordion](#metaaccordion)
				- [meta.@context](#metacontext)
				- [meta.pav:createdBy](#metapavcreatedby)
				  - [@id](#id)
				- [meta.pav:lastUpdatedOn](#metapavlastupdatedon)
				- [meta.oslc:modifiedBy](#metaoslcmodifiedby)
				  - [@id](#id)
				- [meta.schema:name](#metaschemaname)
				- [meta.respondent](#metarespondent)
				- [meta.screens](#metascreens)
				  - [[screen]](#screen)
				- [meta.status](#metastatus)
	- [Schedules](#schedules)
		- [[Volume]](#volume)
			- [[Frequency]](#frequency)
			    - [meta.activities](#metaactivities)
			      - [@id](#uidu)
			      - [name](#unameu)
				- [meta.@context](#metacontext)
	- [Screens](#screens)
		- [[Version]](#version)
			- [[Screen]](#screen)
				- [[File]](#file)
				- [meta.@context](#metacontext)
				- [meta.schema:name](#metaschemaname)
				- [meta.options](#metaoptions)
				  - [[option]](#option)
				- [meta.question_image](#metaquestionimage)
				  - [@id](#id)
				- [meta.question_text](#metaquestiontext)
				- [meta.response_type](#metaresponsetype)
- [Users](#users)
	- [[Volume]](#volume)
		- [Responses](#responses)
			- [[Activity]](#activity)
				- [[Version]](#version)
				  - [[Completed Activity]](#completed-activity)
		- [Schedules](#schedules)
			- [[Schedule]](#schedule)
				- [activities](#activities)
			    	- [@id](#id)
			    	- [name](#name)
- [Groups](#groups)
	- [Editors](#editors)
	- [Managers](#managers)
	- [Users](#users)
	- [Viewers](#viewers)

## Collections

### Activities

The **Activities** Collection is organized into a Folder for each [**Activity**].

#### [Activity]

Each **Activities**.[**Activity**] Folder contains an Item for each [**Version**] of that [**Activity**].

##### [Version]
Each **Activities**.[**Activity**].[**Version**] Item contains JSON-LD metadata.

###### meta.abbreviation

String abbreviation for this [**Activity**].[**Version**] (not necessesarily unique).

###### meta.accordion

Boolean, display this [**Activity**].[**Version**]'s **Srceens** in an accordion format instead of a discrete series of screens?

###### meta.@context

JSON-LD object with prefix and type definitions.

###### meta.pav:createdBy

A JSON-LD object with an **@id** key and a value that resolves to the Mindlogger User who created this [**Activity**].[**Version**].

###### *@id*

String in the format "user/[girder_id]".

###### meta.pav:lastUpdatedOn

Datetime of last update.

###### meta.oslc:modifiedBy

Array of JSON-LD objects that resolves to Mindlogger Users who have ever modified this [**Activity**].[**Version**].

###### *@id*

String in the format "user/[girder_id]".

###### meta.schema:name

JSON-LD object with **@language** and **@value** strings.

###### meta.respondent

String (for now) indicating the intended respondent in relationship to the target individual (eg, "Self", "Parent", "Teacher", "Peer").

###### meta.screens

JSON-LD array (ordered) of **Screens** to display, in sequence, for this [**Activity**].[**Version**]. This sequence is the default order that will be presented if the **User** chooses "Skip" on every **Screen**.

###### [*screen*]

Each **meta.screens**.[**screen**] object contains an **@id** key with a string value that resolves to a Mindlogger **Screen** in the Girder API.

###### meta.status

String (for now): "active" or "inactive".

### Schedules

The **Schedules** Collection is organized into a Folder for each [**Volume**].

#### [Volume]

Each [**Volume**] Folder contains a Folder for each relevant [**Frequency**].

##### [Frequency]

Each [**Frequency**] Folder contains assignable [**Frequency**] Items.

###### *meta.activities*

A JSON-LD array (ordered by priority) of **Activities** to be completed with the parent **Frequency**.

###### <u>@id</u>
A string in the format "item/[girder_id]"

###### <u>name</u>
A string to show in the **User**'s app for this **Schedule**.

###### *meta.@context*

JSON-LD object with prefix and type definitions.


### Screens

The **Screens** Collection is organized into a Folder for each [**Activity**].[**Version**].

#### [Version]

Each **Screens**.[**Version**] Folder contains one or more **[Screen]** Items.

##### [Screen]

Each **Screens**.[**Version**].[**Screen**] Item contains JSON-LD metadata, including **@context**, **schema:name**, **options**, **question_image**, **question_text**, **response_type** and any relevant media (images, audio, and/or video files).

###### [File]

An Audio File, Image File or Video File to be presented on the parent [**Screen**].

###### meta.@context

JSON-LD object with prefix and type definitions.


###### meta.schema:name

JSON-LD object with **@language** and **@value** strings.

###### meta.options

JSON-LD array of objects (ordered).

###### *[option]*

Each **Screens**.[**Version**].[**Screen**].**options**.[**option**] contains a stimulus to be presented to the **User** (eg, an **option_text** object JSON-LD object with **@language** and **@value** strings) and a **value** string to be stored / used for scoring if that response **[option]** is chosen.

###### meta.question_image
A JSON-LD object that resolves to an Image URL through the Mindlogger Girder API.

###### *@id*
A string in the format "file/[girder_id]".

###### meta.question_text

JSON-LD object with **@language** and **@value** strings.

###### meta.response_type

String (for now).

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
