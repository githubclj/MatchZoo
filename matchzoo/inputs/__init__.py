# note 
import six
from keras.utils.generic_utils import deserialize_keras_object

from point_generator import PointGenerator

from pair_generator import PairGenerator
from pair_generator import DRMM_PairGenerator
from pair_generator import PairGenerator_Feats
from list_generator import ListGenerator
from list_generator import DRMM_ListGenerator
from list_generator import ListGenerator_Feats

def serialize(generator):
    return generator.__name__

def deserialize(name, custom_objects=None):
    return deserialize_keras_object(name,
                                    module_objects=globals(),
                                    custom_objects=custom_objects,
                                    printable_module_name='loss function')

def get(identifier):
    """Get the object of generator

       According to the identifier,you will get the
       object of generator

    # Arguments
        identifier: The identifier of generator

    # Returns
        The object of generator
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

