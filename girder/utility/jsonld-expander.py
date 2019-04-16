from pyld import jsonld
from copy import deepcopy
import json


def check_for_unexpanded_value_constraints(item_exp):
    vc = item_exp[0]
    if 'https://schema.repronim.org/valueconstraints' in vc.keys():
        vc = vc['https://schema.repronim.org/valueconstraints'][0]
        if isinstance(vc, dict):
            if "@id" in vc.keys():
                return True

    return False


def expand_full(appletURL):
    applet_expanded = jsonld.expand(appletURL)

    activities_expanded = get_activities(applet_expanded)

    items_expanded = get_items(activities_expanded)
    expItems1 = expand_value_constraints(items_expanded)

    # re-expand the items in case any multiparters were added
    expItems2 = expand_value_constraints(expItems1)

    return dict(activities = activities_expanded, items = items_expanded, applet = applet_expanded)


def expand_value_constraints(original_items_expanded):
    items_expanded = deepcopy(original_items_expanded)
    for item, item_exp in original_items_expanded.items():
        # check if we need to expand valueConstraints
        vc = item_exp[0]
        if 'https://schema.repronim.org/valueconstraints' in vc.keys():
            if check_for_unexpanded_value_constraints(item_exp):
                vc = jsonld.expand(item_exp[0]['https://schema.repronim.org/valueconstraints'][0]['@id'])
                items_expanded[item][0]['https://schema.repronim.org/valueconstraints'][0] = vc
        else:
            multipart_activities = get_activities(item_exp)
            items_expanded.update(multipart_activities)
    return items_expanded


def get_activities(applet_expanded):
    activities = [a['@id'] for a in applet_expanded[0]['https://schema.repronim.org/order'][0]['@list']]

    activities_expanded = {a: jsonld.expand(a) for a in activities}
    return activities_expanded


def get_items(activities_expanded):
    items_expanded = {}
    for a in activities_expanded.keys():
        for i in activities_expanded[a][0]['https://schema.repronim.org/order'][0]['@list']:
            items_expanded[i['@id']] = jsonld.expand(i['@id'])
    return items_expanded
