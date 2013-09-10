from PyQt4.QtCore import *

from qgis.core import *

def get_features(layer, use_selected, filter_id=None):
    '''
    Return the features to process.

    Inputs:

        layer - A QgsVectorLayer

        use_selected - A boolean indicating if only the selected features
            should be used

        filter_id - The id of a feature to extract. If None (the default),
            the result will contain all the features (or all the selected
            features in case the use_selected argument isTrue)

    The output can be either a QgsFeatureIterator or a python list
    with the features. Both datatypes are suitable for using inside a
    for loop.

    If the use_selected argument is True but there are no features
    currently selected, all the features in the layer will be returned.
    '''

    features = []
    if use_selected:
        features = layer.selectedFeatures()
        if filter_id is not None:
            features = [f for f in features if f.id() == filter_id]
    if not any(features):
        if filter_id is not None:
            request = QgsFeatureRequest(filter_id)
            features = layer.getFeatures(request)
        else:
            features = layer.getFeatures()
    return features

def get_unique_fields(layer):
    unique_fields = [f for f in layer.dataProvider().fields() \
            if f.type() in (QVariant.Int, QVariant.Double)]
    seen = dict()
    for f in unique_fields:
        seen[f.name()] = []
    request = QgsFeatureRequest()
    request.setFlags(QgsFeatureRequest.NoGeometry)
    for feat in layer.getFeatures(request):
        to_remove = []
        for f in unique_fields:
            name = f.name()
            value = feat.attribute(name)
            if value not in seen[name]:
                seen[name].append(value)
            else:
                to_remove.append(name)
        if len(to_remove) > 0:
            unique_fields = [f for f in unique_fields if \
                    f.name() not in to_remove]
        if not any(unique_fields):
            print('No more unique fields')
            break
    result = [f.name() for f in unique_fields]
    return result 

def get_all_values(layer, fields):
    result = []
    for feat in layer.getFeatures():
        for field in fields:
            result.append({
                'field' : field.name(),
                'value' : feat.attribute(field.name()),
            })
    return result

def exist_selected_features(qgis_layers):
    exist_selected = False
    for layer in qgis_layers:
        if layer.selectedFeatureCount() > 1:
            exist_selected = True
    return exist_selected
