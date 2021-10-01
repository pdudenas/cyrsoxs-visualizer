"""
LineProfile QWidget inspired by and adapted from 

https://github.com/haesleinhuepf/napari-plot-profile 
and 
https://github.com/psobolewskiPhD/napari_scripts/blob/main/napari_line_profile_widget.py


ClippingPlanes QWidget inspired by and adapted from 

https://github.com/napari/napari/blob/b39647d94e587f0255b0d4cc3087855e160a8929/examples/clipping_planes_interactive.py

It implements the ``napari_experimental_provide_dock_widget`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html

Replace code below according to your needs.
"""
from napari_plugin_engine import napari_hook_implementation
from qtpy.QtWidgets import QWidget, QGridLayout, QRadioButton, QPushButton, QVBoxLayout, QHBoxLayout
from magicgui import widgets

from skimage import measure
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure

import napari


class LineProfiler(QWidget):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def __init__(self, napari_viewer):
        super().__init__(napari_viewer.window.qt_viewer)
        self.viewer = napari_viewer
        self.viewer.axes.visible = True
        self.viewer.dims.axis_labels = ('y','x')
        self.canvas = FigureCanvas(Figure(figsize=(2,4)))
        self.ax = self.canvas.figure.subplots()
        self.layout = QGridLayout()
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)

        self.shapes_layer = self.viewer.add_shapes(
            np.array([[0,0],[128,128]]),
            shape_type='line',
            edge_width=2,
            edge_color='black',
            face_color='black'
        )
        self.shapes_layer.mode = 'select'

        self.lines = []
        self.profile_lines()

        # connect mouse drag callback
        self.shapes_layer.mouse_drag_callbacks.append(self._profile_lines_drag)

        # update when a layer is made in/visible
        self.viewer.layers.events.connect(self._update_visibility)

        # update when a layer is removed
        self.viewer.layers.events.removed.connect(self._remove_extra_lines)

        # update when an image is loaded
        self.viewer.layers.events.connect(self._on_load)

        # # print out event
        # napari.utils.events.connect(self.print_event)

    def _get_line(self):
        line = None
        for layer in self.viewer.layers:
            if isinstance(layer, napari.layers.Shapes):
                try:
                    line = layer.data[-1]
                except IndexError:
                    pass
        return line        
    
    def get_line_data(self, image, start, end):
        if image.ndim == 2:
            return measure.profile_line(image, start, end, mode='reflect')
        else:
            slice_nr = self.viewer.dims.current_step[0]
            return measure.profile_line(image[slice_nr], start, end, mode='reflect')
    
    def get_image_layers(self):
        return [layer for layer in self.viewer.layers if isinstance(layer, napari.layers.Image)]

    def profile_lines(self):
        line = self._get_line()
        if line is None:
            return
        image_layers = self.get_image_layers()
        for j, selected_layer in enumerate(image_layers):
            if selected_layer.visible != 0:
                y = self.get_line_data(selected_layer.data,*line)
                x = np.arange(len(y))
                try:
                    self.lines[j][0].set_data(x,y)
                    self.lines[j][0].set_label(selected_layer.name)
                except IndexError:
                    self.lines.append(self.ax.plot(self.get_line_data(selected_layer.data,*line),
                                                label=selected_layer.name))
            elif selected_layer.visible == 0:
                x = []
                y = []
                self.lines[j][0].set_data(x,y)
        
        self.ax.relim()
        self.ax.legend()
        self.ax.autoscale_view()
        self.canvas.draw()
    
    
    def _remove_extra_lines(self, event):
        if len(self.lines) > len(self.get_image_layers()):
            self.lines.pop(-1)
            self.ax.lines.pop(-1)

        self.profile_lines()

    def _profile_lines_drag(self, layer, event):
        self.profile_lines()
        yield
        while event.type =='mouse_move':
            self.profile_lines()
            yield
    
    def _update_visibility(self, event):
        # print('entered visibility function')
        if event.type == 'visible':
            self.profile_lines()
    
    def _on_load(self, event):
        if event.type =='set_data':
            self.profile_lines()
    
    # # For figuring out what events are happening
    # def print_event(self, event):
    #     print(event, event.type)


class ClippingPlanes(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.viewer.axes.visible = True
        self.viewer.camera.angles = (45, 45, 45)
        self.viewer.dims.axis_labels = ('z','y','x')


        self.plane_parameters = {
            'position': (32, 32, 32),
            'normal': (0, 0, 1),
            'enabled': True
        }

        self.layout = QVBoxLayout()
        self.choices = {'XY':(0,0,1),'XZ':(0,1,0),'YZ':(1,0,0),'XYZ':(1,1,1)}
        self.angles = {'XY':(45,45,90),'XZ':(45,90,45),'YZ':(90,45,45),'XYZ':(45,45,45)}
        for i, choice in enumerate(self.choices):
            btn = QRadioButton(choice)
            # print(dir(btn))
            if i == 0:
                btn.setChecked(True)
            btn.toggled.connect(self._update_plane_normal)
            self.layout.addWidget(btn)
        self.visible_button = QPushButton()
        self.visible_button.setText('Make Clipping Plane Invisible')
        self.visible_button.clicked.connect(self._update_clipping_visibility)
        self.layout.addWidget(self.visible_button)
        self.layout.addStretch()
        self.setLayout(self.layout)

        self.viewer.mouse_drag_callbacks.append(self.shift_plane_along_normal)
        self.viewer.layers.events.connect(self._on_load)

        for layer in self.viewer.layers:
            layer.experimental_clipping_planes = self.plane_parameters

    def point_in_bounding_box(self, point, bounding_box):
        if np.all(point > bounding_box[0]) and np.all(point < bounding_box[1]):
            return True
        return False

    def get_image_layers(self):
        return [layer for layer in self.viewer.layers if isinstance(layer, napari.layers.Image)]


    def shift_plane_along_normal(self, viewer, event):
        """Shift a plane along its normal vector on mouse drag.
        This callback will shift a plane along its normal vector when the plane is
        clicked and dragged. The general strategy is to
        1) find both the plane normal vector and the mouse drag vector in canvas
        coordinates
        2) calculate how far to move the plane in canvas coordinates, this is done
        by projecting the mouse drag vector onto the (normalised) plane normal
        vector
        3) transform this drag distance (canvas coordinates) into data coordinates
        4) update the plane position
        It will also add a point to the points layer for a 'click-not-drag' event.
        """
        # # get layers from viewer
        # volume_layer = self.viewer.layers['volume']

        # grab first image layer as 'volume'
        image_layers = self.get_image_layers()
        try:
            self.volume_layer = image_layers[0]
        except IndexError:
            # no image layers, grab first layer in viewer
            self.volume_layer = [layer for layer in self.viewer.layers][0]

        # Calculate intersection of click with data bounding box
        near_point, far_point = self.volume_layer.get_ray_intersections(
            event.position,
            event.view_direction,
            event.dims_displayed,
        )

        # Calculate intersection of click with plane through data
        intersection = self.volume_layer.experimental_clipping_planes[0].intersect_with_line(
            line_position=near_point, line_direction=event.view_direction
        )

        # Check if click was on plane by checking if intersection occurs within
        # data bounding box. If so, exit early.
        if not self.point_in_bounding_box(intersection, self.volume_layer.extent.data):
            return

        # Get plane parameters in vispy coordinates (zyx -> xyz)
        plane_normal_data_vispy = np.array(self.volume_layer.experimental_clipping_planes[0].normal)[[2, 1, 0]]
        plane_position_data_vispy = np.array(self.volume_layer.experimental_clipping_planes[0].position)[[2, 1, 0]]

        # Get transform which maps from data (vispy) to canvas
        visual2canvas = self.viewer.window.qt_viewer.layer_to_visual[self.volume_layer].node.get_transform(
            map_from="visual", map_to="canvas"
        )

        # Find start and end positions of plane normal in canvas coordinates
        plane_normal_start_canvas = visual2canvas.map(plane_position_data_vispy)
        plane_normal_end_canvas = visual2canvas.map(plane_position_data_vispy + plane_normal_data_vispy)

        # Calculate plane normal vector in canvas coordinates
        plane_normal_canv = (plane_normal_end_canvas - plane_normal_start_canvas)[[0, 1]]
        plane_normal_canv_normalised = (
                plane_normal_canv / np.linalg.norm(plane_normal_canv)
        )

        # Disable interactivity during plane drag
        for layer in self.viewer.layers:
            layer.interactive = False

        # Store original plane position and start position in canvas coordinates
        original_plane_position = self.volume_layer.experimental_clipping_planes[0].position
        start_position_canv = event.pos

        yield
        while event.type == "mouse_move":
            # Get end position in canvas coordinates
            end_position_canv = event.pos

            # Calculate drag vector in canvas coordinates
            drag_vector_canv = end_position_canv - start_position_canv

            # Project the drag vector onto the plane normal vector
            # (in canvas coorinates)
            drag_projection_on_plane_normal = np.dot(
                drag_vector_canv, plane_normal_canv_normalised
            )

            # Update position of plane according to drag vector
            # only update if plane position is within data bounding box
            drag_distance_data = drag_projection_on_plane_normal / np.linalg.norm(plane_normal_canv)
            updated_position = original_plane_position + drag_distance_data * np.array(
                self.volume_layer.experimental_clipping_planes[0].normal)

            if self.point_in_bounding_box(updated_position, self.volume_layer.extent.data):
                for layer in viewer.layers:
                    layer.experimental_clipping_planes[0].position = updated_position

            yield

        # Re-enable
        for layer in self.viewer.layers:
            layer.interactive = True
    

    def _update_plane_normal(self):
        rbtn = self.sender()

        if rbtn.isChecked() == True:
            self.plane_parameters['normal'] = self.choices[rbtn.text()]
            for layer in self.viewer.layers:
                layer.experimental_clipping_planes[0].normal = self.choices[rbtn.text()]
            # print(self.plane_parameters['normal'])
    
    def _update_clipping_visibility(self):
        if self.plane_parameters['enabled']:
            self.plane_parameters['enabled'] = False
            self.visible_button.setText('Make Clipping Plane Visible')
            for layer in self.viewer.layers:
                layer.experimental_clipping_planes[0].enabled = False
        else:
            self.plane_parameters['enabled'] = True
            self.visible_button.setText('Make Clipping Plane Invisible')
            for layer in self.viewer.layers:
                layer.experimental_clipping_planes[0].enabled = True
        
        # print(self.plane_parameters['enabled'])

    # def print_event(self, event):
    #     print(event,event.type)
    
    def _on_load(self, event):
        if event.type == 'inserted':
            for layer in self.viewer.layers:
                layer.experimental_clipping_planes = self.plane_parameters




@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    # you can return either a single widget, or a sequence of widgets
    return [(LineProfiler, {'area':'bottom','name':'Line Profiler'}),
            (ClippingPlanes, {'area':'right','name':'3D Clipping Plane'})]
