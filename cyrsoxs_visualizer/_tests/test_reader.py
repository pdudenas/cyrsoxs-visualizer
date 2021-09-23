import numpy as np
from cyrsoxs_visualizer import napari_get_reader
import h5py


# tmp_path is a pytest fixture
def test_reader(tmp_path):
    """An example of how you might test your plugin."""

    # write some fake data using your supported file format
    my_test_file = str(tmp_path / "myfile.hd5")
    original_data_unaligned = np.random.rand(20, 20)
    original_data_aligned = np.random.rand(20,20,3)
    with h5py.File(my_test_file,'w') as f:
        f.create_dataset('igor_parameters/igormaterialnum',data=2.0)
        f.create_dataset('vector_morphology/Mat_1_unaligned',data=original_data_unaligned)
        f.create_dataset('vector_morphology/Mat_1_alignment',data=original_data_aligned)


    # try to read it back in
    reader = napari_get_reader(my_test_file)
    assert callable(reader)

    # make sure we're delivering the right format
    layer_data_list = reader(my_test_file)
    assert isinstance(layer_data_list, list) and len(layer_data_list) > 0
    layer_data_tuple = layer_data_list[0]
    assert isinstance(layer_data_tuple, tuple) and len(layer_data_tuple) > 0

    # make sure it's the same as it started
    np.testing.assert_allclose(original_data, layer_data_tuple[0])


def test_get_reader_pass():
    reader = napari_get_reader("fake.file")
    assert reader is None
