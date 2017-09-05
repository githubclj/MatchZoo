# note:
import six
from keras.utils.generic_utils import deserialize_keras_object
from .evaluations import map
from .evaluations import ndcg
from .evaluations import precision
from .evaluations import mrr
from .evaluations import mse

def serialize(generator):
    return generator.__name__

def deserialize(name, custom_objects=None):
    return deserialize_keras_object(name,
                                    module_objects=globals(),
                                    custom_objects=custom_objects,
                                    printable_module_name='loss function')

def get(identifier):
    """Get the object of metrics

       According to the identifier,you will get the
       object of metrics

    # Arguments
        identifier: The identifier of metrics

    # Returns
        The object of metrics
    """
    if identifier is None:
        return None
    if isinstance(identifier, six.string_types):
        identifier = str(identifier)
        return deserialize(identifier)
    elif callable(identifier):
        return identifier
    else:
        raise ValueError('Could not interpret '
                         'loss function identifier:', identifier)

