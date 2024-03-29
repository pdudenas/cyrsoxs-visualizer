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
import os


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
    if path.endswith(".hd5") or path.endswith(".hdf5"):
        return read_hdf5

    # otherwise we return the *function* that can read ``path``.
    return none


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
        num_mat = int(h5['igor_parameters/igormaterialnum'][()])
        for i in range(num_mat-1): # don't include vacuum
            # unaligned material
            phi = h5[f'vector_morphology/Mat_{i+1}_unaligned'][()]
            layer_data_list.append((phi,{'name':f'Mat_{i+1}_unaligned'},"image"))
            # alignment vectors
            s = h5[f'vector_morphology/Mat_{i+1}_alignment'][()]

            # reshape from (Z,Y,X,D) array to (N,2,D) array (list) of vectors
            smag = np.sqrt(np.sum(s**2,axis=-1))
            idx = smag > 0
            vector_pos = np.column_stack(np.where(idx))
            if len(vector_pos) != 0:
                vectors = np.zeros((len(vector_pos),2,phi.ndim))
                vectors[:,0,:] = vector_pos
                vectors[:,1,:] = s[idx]

                layer_data_list.append((vectors,{'name':f'Mat_{i+1}_alignment','visible':False,'edge_width':0.1},"vectors"))
    
    return layer_data_list
