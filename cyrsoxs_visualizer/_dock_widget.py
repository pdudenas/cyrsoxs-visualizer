"""
LineProfile QWidget

Inspired by and adapted from 

https://github.com/haesleinhuepf/napari-plot-profile 
and 
https://github.com/psobolewskiPhD/napari_scripts/blob/main/napari_line_profile_widget.py

It implements the ``napari_experimental_provide_dock_widget`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html

Replace code below according to your needs.
"""
from napari_plugin_engine import napari_hook_implementation
# from qtpy.QtWidgets import QWidget, QHBoxLayout, QPushButton

from skimage import measure
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure

import napari


class LineProfiler():
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.viewer.axes.visible = True
        self.viewer.dims.axis_labels = ('y','x')
        self.canvas = FigureCanvas(Figure(figsize=(2,4)))
        self.ax = self.canvas.figure.subplots()

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

        # add plot below imagge
        self.viewer.window.add_dock_widget(self.canvas, area='bottom')

        # connect mouse drag callback
        self.shapes_layer.mouse_drag_callbacks.append(self.profile_lines_drag)

        # update when a layer is made in/visible
        self.viewer.layers.events.connect(self._update_visibility)

        # update when an image is loaded
        # self.viewer.layers.events.connect(self._on_load)

        # # print out event
        # self.viewer.layers.events.connect(self.print_event)

    def _get_line(self):
        line = None
        for layer in self.viewer.layers:
            if isinstance(layer, napari.layers.Shapes):
                line = layer.data[-1]
        return line        
    
    def get_line_data(self, image, start, end):
        return measure.profile_line(image, start, end, mode='reflect')
    
    def profile_lines(self):
        line = self._get_line()

        for j, selected_layer in enumerate(self.viewer.layers):
            if isinstance(selected_layer,napari.layers.Image) and selected_layer.visible != 0:
                y = self.get_line_data(selected_layer.data,*line)
                x = np.arange(len(y))
                try:
                    self.lines[j][0].set_data(x,y)
                except IndexError:
                    self.lines.append(self.ax.plot(self.get_line_data(selected_layer.data,*line),
                                                label=selected_layer.name))
            elif isinstance(selected_layer,napari.layers.Image) and selected_layer.visible == 0:
                x = []
                y = []
                self.lines[j][0].set_data(x,y)
        
        self.ax.relim()
        self.ax.legend()
        self.ax.autoscale_view()
        self.canvas.draw()
    
    
    
    def profile_lines_drag(self, layer, event):
        self.profile_lines()
        yield
        while event.type =='mouse_move':
            self.profile_lines()
            yield
    
    def _update_visibility(self,event):
        # print('entered visibility function')
        if event.type == 'visible':
            self.profile_lines()
    
    # def _on_load(self, event):
    #     if event.type =='set_data':
    #         self.profile_lines()
    #         for layer in self.viewer.layers:
    #             if isinstance(layer, napari.layers.Shapes):
    #                 # not working at the moment
    #                 layer.move_to_front() 
    
    # # For figuring out what events are happening
    # def print_event(self, event):
    #     print(event.type)

@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    # you can return either a single widget, or a sequence of widgets
    return [LineProfiler]
