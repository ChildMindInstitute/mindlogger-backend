import datetime

from bson import ObjectId
from girderformindlogger.models.events import Events as EventsModel
from girderformindlogger.models.account_profile import AccountProfile

model = EventsModel()
events = model.find({})

for event in events:
    model.setSchedule(event)
    model.save(event)

