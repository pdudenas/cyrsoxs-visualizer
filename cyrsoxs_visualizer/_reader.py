"""
This module is an example of a barebones numpy reader plugin for napari.

It implements the ``napari_get_reader`` hook specification, (to create
a reader plugin) but your plugin may choose to implement any of the hook
specifications offered by napari.
see: https://napari.org/docs/dev/plugins/hook_specifications.html

Replace code below accordingly.  For complete documentation see:
https://napari.org/docs/dev/plugins/for_plugin_developers.html
"""
import numpy as np
import h5py
from napari_plugin_engine import napari_hook_implementation
from skimage.transform import pyramid_gaussian


@napari_hook_implementation
def napari_get_reader(path):
    """A basic implementation of the napari_get_reader hook specification.

    Parameters
    ----------
    path : str or list of str
        CyRSoXS morphology hdf5 file

    Returns
    -------
    Callable or None
        CyRSoXS hdf5 reader if the path file extension is correct
    """
    if isinstance(path, list):
        # reader plugins may be handed single path, or a list of paths.
        # if it is a list, it is assumed to be an image stack...
        # so we are only going to look at the first file.
        path = path[0]

    # if we know we cannot read the file, we immediately return None.
    if not path.endswith(".hd5"):
        return None

    # otherwise we return the *function* that can read ``path``.
    return read_hdf5


def read_hdf5(path: str):
    """Returns a list of LayerData tuples from the morphology hdf5

    Readers are expected to return data as a list of tuples, where each tuple
    is (data, [add_kwargs, [layer_type]]), "add_kwargs" and "layer_type" are
    both optional.

    Parameters
    ----------
    path : str or list of str
        Path to file, or list of paths.

    Returns
    -------
    layer_data : list of tuples
        A list of LayerData tuples where each tuple in the list contains
        (data, metadata, layer_type), where data is a numpy array, metadata is
        a dict of keyword arguments for the corresponding viewer.add_* method
        in napari, and layer_type is a lower-case string naming the type of layer.
        Both "meta", and "layer_type" are optional. napari will default to
        layer_type=="image" if not provided
    """
    with h5py.File(path, 'r') as h5:
        layer_data_list = []
        num_mat = h5['igor_parameters/igormaterialnum'][()]
        for i in range(num_mat):
            phi = h5[f'vector_morphology/Mat_{i+1}_unaligned'][()]
            s = h5[f'vector_morphology/Mat_{i+1}_alignment'][()]
            layer_data_list.append((phi,{'name':f'Mat_{i+1}_unaligned'},"image"))
            layer_data_list.append((s,{'name':f'Mat_{i+1}_alignment'},"vectors"))
    return layer_data_list
