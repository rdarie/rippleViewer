from re import L
from ephyviewer.myqt import QT
# from pyqtgraph.util.mutex import Mutex
from contextlib import nullcontext
import numpy as np
from pyRippleViewer.tridesclous.base import WidgetBase
import logging
from ephyviewer.base_vispy import MyQtSceneCanvas
import time

LOGGING = False
logger = logging.getLogger(__name__)

from vispy import scene

dataio_param_names = ['left_sweep', 'right_sweep', 'stack_size']

default_factor_y = 0.5

import pdb

class RippleWaveformViewer(WidgetBase):
    _params = [
        {'name': 'plot_individual_spikes', 'type': 'list', 'value': 'last', 'values': ['last', 'selected', 'none']},
        {'name': 'individual_spikes_num', 'type' :'int', 'value' : 5, 'limits':[1, np.inf]},
        {'name': 'show_only_selected_cluster', 'type': 'bool', 'value': False},
        {'name': 'plot_limit_for_flatten', 'type': 'bool', 'value': True},
        {'name': 'plot_zero_vline', 'type': 'bool', 'value': True},
        {'name': 'plot_zero_hline', 'type': 'bool', 'value': True},
        {'name': 'summary_statistics', 'type': 'list', 'value': 'none', 'values': ['median/mad', 'none'] },
        {'name': 'shade_dispersion', 'type': 'bool', 'value': False},
        {'name': 'show_channel_num', 'type': 'bool', 'value': True},
        {'name': 'show_scalebar', 'type': 'bool', 'value': True},
        {'name': 'zero_line_color', 'type': 'color', 'value': '#FFFFFFAA'},
        {'name': 'max_num_points', 'type' :'int', 'value' : 500000, 'limits':[2000, np.inf]},
        {'name': 'debounce_sec', 'type' :'float', 'value' : 330e-3, 'limits':[10e-3, np.inf]},
        {'name': 'left_sweep', 'type': 'float', 'value': -10e-3, 'step': 50e-3,'suffix': 's', 'siPrefix': True},
        {'name': 'right_sweep', 'type': 'float', 'value': 40e-3, 'step': 50e-3, 'suffix': 's', 'siPrefix': True},
        {'name': 'stack_size', 'type' :'int', 'value' : 1000,  'limits':[1, np.inf] },
        {'name': 'linewidth', 'type' :'float', 'value' : 1, 'limits':[0.5, 5]},
        {'name': 'y_scaling_factor', 'type' :'float', 'value' : 1, 'limits':[0., np.inf]},
        {'name': 'linewidth_mean', 'type' :'float', 'value' : 2, 'limits':[0.5, 5]},
        {'name': 'geometry_aspect_ratio', 'type' :'float', 'value' : 1, 'limits':[0.5, 10]},
        # {'name': 'flip_bottom_up', 'type': 'bool', 'value': False},
        # {'name': 'display_threshold', 'type': 'bool', 'value' : False},
        # {'name': 'sparse_display', 'type': 'bool', 'value' : False },
        ]

    def __init__(
            self, controller=None, parent=None, refreshRateHz=1.):

        WidgetBase.__init__(
            self, parent=parent,
            controller=controller, refreshRateHz=refreshRateHz)

        self.sample_rate = self.controller.dataio.sample_rate

        remakeIOStack = False
        for paramName in ['left_sweep', 'right_sweep']:
            if self.controller.dataio.params[paramName] != self.params[paramName]:
                self.controller.dataio.params[paramName] = self.params[paramName]
                remakeIOStack = True
        if remakeIOStack:
            self.controller.dataio.remake_stack()
            self.controller.dataio.make_centroids()
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)

        self.create_toolbar()
        self.layout.addWidget(self.toolbar)

        self.sceneCanvas = MyQtSceneCanvas(
            parent=self, keys='interactive', show=True)
        self.layout.addWidget(self.sceneCanvas)

        #
        self.grid = self.sceneCanvas.central_widget.add_grid(margin=0)

        self.plot1 = None
        self.plot2 = None

        self.xaxis1 = None
        self.xaxis2 = None

        self.yaxis1 = None
        self.yaxis2 = None

        self.show_xaxis_geometry = False
        self.show_yaxis_geometry = False

        self.show_xaxis_flatten = False
        self.show_yaxis_flatten = True

        self.alpha = 60

        # adjust widget size
        thisQSize = self.sizeHint()
        thisQSizePolicy = self.sizePolicy()
        thisQSizePolicy.setHorizontalPolicy(QT.QSizePolicy.MinimumExpanding)
        thisQSizePolicy.setVerticalPolicy(QT.QSizePolicy.MinimumExpanding)
        thisQSizePolicy.setHorizontalStretch(10)
        self.setSizePolicy(thisQSizePolicy)
        self.setMinimumSize(thisQSize.width(), thisQSize.height())

        self.last_individual_wf = None
        self.wf_min, self.wf_max = 0, 0
        self.wf_dispersion_min, self.wf_dispersion_max = 0, 1

        self.channel_title_params = dict(
            color='white',
            font_size=10,
            anchor_x='center', anchor_y='top',
            )
        self.scalebar_params = dict(
            minor_tick_length=4,
            major_tick_length=8,
            tick_font_size=8,
            tick_label_margin=4,
            axis_font_size=10,
            axis_label_margin=4,
            anchors=('center', 'bottom')
            )

        self.axes_params = dict(
            minor_tick_length=6,
            major_tick_length=10,
            tick_font_size=8,
            tick_label_margin=6,
            axis_font_size=10,
            axis_label_margin=16,
            anchors=('center', 'bottom')
            )
        
        self.sceneCanvas.ygain_zoom.connect(self.gain_zoom)
        self.sceneCanvas.doubleclicked.connect(self.open_settings)

        self.factor_y = default_factor_y

        chan_grp = self.controller.chan_grp
        channel_group = self.controller.dataio.channel_groups[chan_grp]
        if channel_group['geometry'] is None:
                print('no geometry')
        else:
            self.arr_geometry = []
            for i, chan in enumerate(self.controller.channel_indexes):
                x, y = channel_group['geometry'][chan]
                self.arr_geometry.append([x, y])
            self.arr_geometry = np.array(self.arr_geometry, dtype='float64')
            # if self.params['flip_bottom_up']:
            #     self.arr_geometry[:, 1] *= -1.
            xpos = self.arr_geometry[:, 0]
            ypos = self.arr_geometry[:, 1]
            if np.unique(xpos).size > 1:
                # self.delta_x = np.min(np.diff(np.sort(np.unique(xpos))))
                self.delta_x = np.min(np.diff(np.unique(xpos)))
            else:
                self.delta_x = np.unique(xpos)[0]
            if np.unique(ypos).size > 1:
                # self.delta_y = np.min(np.diff(np.sort(np.unique(ypos))))
                self.delta_y = np.min(np.diff(np.unique(ypos)))
            else:
                self.delta_y = max(np.unique(ypos)[0], 1)
            if self.delta_x > 0.:
                self.espx = self.delta_x / (2 * 1.1 * self.params['geometry_aspect_ratio'])
            else:
                self.espx = .5
            # squeeze empty rows and colums
            self.arr_geometry_indexed = np.zeros_like(self.arr_geometry, dtype=int)
            self.arr_geometry_indexed[:, 0] = np.asarray(self.arr_geometry[:, 0] / self.delta_x, dtype=int)
            self.arr_geometry_indexed[:, 1] = np.asarray(self.arr_geometry[:, 1] / self.delta_y, dtype=int)
            indexes_min = self.arr_geometry_indexed.min(axis=0)
            indexes_max = self.arr_geometry_indexed.max(axis=0)
            offsets = [2 * self.espx, 0.9 * self.delta_y]
            
            for axisIdx in [0]:
                for i in np.arange(indexes_min[axisIdx], indexes_max[axisIdx] + 1):
                    if i not in self.arr_geometry_indexed[:, axisIdx]:
                        mask = self.arr_geometry_indexed[:, axisIdx] > i
                        self.arr_geometry[mask, axisIdx] -= offsets[axisIdx]
        
        self.initialize_plot()
        self.refresh()
    
    def create_toolbar(self):
        tb = self.toolbar = QT.QToolBar()
        
        #Mode flatten or geometry
        self.combo_mode = QT.QComboBox()
        tb.addWidget(self.combo_mode)
        #self.mode = 'flatten'
        #self.combo_mode.addItems(['flatten', 'geometry'])
        self.mode = 'geometry'
        self.combo_mode.addItems(['geometry', 'flatten'])
        self.combo_mode.currentIndexChanged.connect(self.on_combo_mode_changed)
        tb.addSeparator()
        
        but = QT.QPushButton('settings')
        but.clicked.connect(self.open_settings)
        tb.addWidget(but)

        but = QT.QPushButton('reset zoom')
        but.clicked.connect(self.reset_zoom)
        tb.addWidget(but)
        '''
        but = QT.QPushButton('refresh')
        but.clicked.connect(self.refresh)
        tb.addWidget(but)'''

    def reset_zoom(self):
        #
        if self._x_range is not None:
            if self._y1_range is not None:
                self.viewbox1.camera.set_range(x=self._x_range, y=self._y1_range, margin=0.)
            if self._y2_range is not None:
                self.viewbox2.camera.set_range(x=self._x_range, y=self._y2_range, margin=0.)
        self.enableRefresh()
        return
    
    def on_combo_mode_changed(self):
        self.mode = str(self.combo_mode.currentText())
        self.initialize_plot()
        self.enableRefresh()
        return
    
    def on_params_changed(self, params, changes):
        for param, change, data in changes:
            if change != 'value': continue
            # if param.name() == 'flip_bottom_up':
            #     self.initialize_plot()
            '''
            if param.name() == 'plot_individual_spikes':
                if data == 'none':
                    for idx in range(self.params['individual_spikes_num']):
                        curve = self.curves_individual[idx]
                        curve.visible = False'''
            if param.name() == 'individual_spikes_num':
                self.initialize_plot()
            if param.name() == 'debounce_sec':
                # print(f"param_change_data = {data}")
                self.controller.dataio.set_debounce(data)
            if param.name() in dataio_param_names:
                self.controller.dataio.params[param.name()] = data
                self.controller.dataio.remake_stack()
                self.controller.dataio.make_centroids()
                self.initialize_plot()
        self.clear_plots()
        return

    def initialize_plot(self):
        if LOGGING: logger.info(f'WaveformViewer.initialize_plot')
        if self.connectedToIO:
            self.controller.dataio.new_spikes.disconnect(self.refresh)
            self.connectedToIO = False
        self._initialize_plot()
        if not self.connectedToIO:
            self.controller.dataio.new_spikes.connect(self.refresh)
            self.connectedToIO = True

    def clear_plots(self):
        for curve in self.curves_individual:
            curve.visible = False
        for idx, k in enumerate(self.controller.positive_cluster_labels):
            self.curves_geometry[idx].visible = False
            if self.mode == 'flatten':
                self.curves_mad_top[idx].visible = False
                self.curves_mad_bottom[idx].visible = False
                self.curves_mad_plot2[idx].visible = False
        
    def add_blank_curve(self, k):
        if self.connectedToIO:
            self.controller.dataio.new_spikes.disconnect(self.refresh)
            self.connectedToIO = False
        #
        color = self.controller.qcolors.get(k, QT.QColor('white')).getRgbF()
        #
        color2 = QT.QColor(self.controller.qcolors.get(k, QT.QColor('white')))
        color2.setAlpha(self.alpha)
        color2 = color2.getRgbF()
        #
        curve = scene.Line(
            pos=None, color=color, width=self.params['linewidth_mean'],
            parent=self.viewbox1.scene)
        self.curves_geometry.append(curve)
        #
        curve_top = scene.Line(
            pos=None, color=color, width=self.params['linewidth'],
            parent=self.viewbox1.scene)
        curve_top.visible = (self.mode == 'flatten')
        self.curves_mad_top.append(curve_top)
        curve_bottom = scene.Line(
            pos=None, color=color, width=self.params['linewidth'],
            parent=self.viewbox1.scene)
        curve_bottom.visible = (self.mode == 'flatten')
        self.curves_mad_bottom.append(curve_bottom)
        # TODO! fillbetween from Polygon
        # fill = pg.FillBetweenItem(curve1=curve_top, curve2=curve_bottom, brush=color2)
        # self.plot1.addItem(fill)
        # self.curves_mad_fill.append(fill)
        curve_p2 = scene.Line(
            pos=None, color=color, width=self.params['linewidth'],
            parent=self.viewbox2.scene)
        curve_p2.visible = (self.mode == 'flatten')
        self.curves_mad_plot2.append(curve_p2)
        #
        if not self.connectedToIO:
            self.controller.dataio.new_spikes.connect(self.refresh)
            self.connectedToIO = True

    def reset_y_factor(self):

        if self.wf_min == 0 and self.wf_max == 0:
            # if the summary stats are missing, maybe we can calculate them now?
            self.controller.dataio.compute_all_centroid()
            self.wf_min, self.wf_max = self.controller.get_min_max_centroids()
            self.wf_dispersion_min, self.wf_dispersion_max = self.controller.get_min_max_dispersions()

        if self.wf_min == 0 and self.wf_max == 0:
            # if the summary stats are still missing, approximate them basesd on
            # the last plotted individual waveform
            if self.last_individual_wf is not None:
                # pdb.set_trace()
                # TODO: implement this
                pass

        if self.wf_min == 0 and self.wf_max == 0:
            self.factor_y = default_factor_y
        else:
            y_range = self.wf_max - self.wf_min
            self.factor_y = (1.1 * y_range) ** (-1)

    def gain_zoom(self, factor_ratio):
        self.factor_y *= factor_ratio
        self.enableRefresh()
    
    def recalc_y_range(self):
        self.wf_min, self.wf_max = self.controller.get_min_max_centroids()
        self.wf_dispersion_min, self.wf_dispersion_max = self.controller.get_min_max_dispersions()
        #
        if self.mode == 'flatten':
            y_domain_length = self.wf_max - self.wf_min
            if y_domain_length > 0:
                y_domain_center = (self.wf_max + self.wf_min) / 2
            else:
                y_domain_center = 0
                y_domain_length = 2
            self._y1_range = (
                y_domain_center - 1.1 * y_domain_length / 2,
                y_domain_center + 1.1 * y_domain_length / 2)
            if self.wf_dispersion_max == 0:
                self._y2_range = 0, 1
            else:
                self._y2_range = 0., self.wf_dispersion_max
        elif self.mode == 'geometry':
            self._y1_range = (
                np.min(self.arr_geometry[:, 1]) - self.delta_y,
                np.max(self.arr_geometry[:, 1]) + self.delta_y
                )
            self._y2_range = None

    def recalc_x_range(self):
        if self.xvect is not None:
            if self.mode == 'flatten':
                self._x_range = self.xvect[0], self.xvect[-1]
            elif self.mode == 'geometry':
                self._x_range = np.min(self.xvect) - self.espx, np.max(self.xvect) + self.espx

    def _initialize_plot(self):
        if self.controller.get_waveform_left_right()[0] is None:
            return

        if self.plot1 is not None:
            self.grid.remove_widget(self.plot1)
            self.plot1.parent = None

        if self.xaxis1 is not None:
            self.plot1.remove_widget(self.xaxis1)
            self.xaxis1.parent = None
        if self.yaxis1 is not None:
            self.plot1.remove_widget(self.yaxis1)
            self.yaxis1.parent = None

        if self.plot2 is not None:
            self.grid.remove_widget(self.plot2)
            self.plot2.parent = None

        if self.xaxis2 is not None:
            self.plot2.remove_widget(self.xaxis2)
            self.xaxis2.parent = None
        if self.yaxis2 is not None:
            self.plot2.remove_widget(self.yaxis2)
            self.yaxis2.parent = None

        self.plot1 = scene.Grid()
        self.plot2 = scene.Grid()

        if self.mode == 'flatten':
            plot1_pos = dict(row=0, row_span=2, col=0)
            self.grid.add_widget(widget=self.plot1, **plot1_pos)

            plot2_pos = dict(row=2, row_span=1, col=0)
            self.grid.add_widget(widget=self.plot2, **plot2_pos)
            
            if self.show_xaxis_flatten and self.show_yaxis_flatten:
                xaxis_pos =   dict(row=1, col=1)
                yaxis_pos =   dict(row=0, col=0)
                viewbox_pos = dict(row=0, col=1)
            elif self.show_xaxis_flatten and (not self.show_yaxis_flatten):
                xaxis_pos   = dict(row=1, col=0)
                yaxis_pos   = None
                viewbox_pos = dict(row=0, col=0)
            elif (not self.show_xaxis_flatten) and self.show_yaxis_flatten:
                xaxis_pos   = None
                yaxis_pos   = dict(row=0, col=0)
                viewbox_pos = dict(row=0, col=1)
            else:
                xaxis_pos   = None
                yaxis_pos   = None
                viewbox_pos = dict(row=0, col=0)

            self.viewbox1 = self.plot1.add_view(camera='panzoom', **viewbox_pos)
            self.viewbox2 = self.plot2.add_view(camera='panzoom', **viewbox_pos)
            
            if self.show_xaxis_flatten:
                xaxis_label = "Time (sec)"
                self.xaxis1 = scene.AxisWidget(
                    orientation='bottom',
                    axis_label=xaxis_label,
                    **self.axes_params)
                self.xaxis1.height_max = 40
                self.plot1.add_widget(self.xaxis1, **xaxis_pos)
                self.xaxis1.link_view(self.viewbox1)
                
                self.xaxis2 = scene.AxisWidget(
                    orientation='bottom',
                    axis_label=xaxis_label,
                    **self.axes_params)
                self.xaxis2.height_max = 40
                self.plot2.add_widget(self.xaxis2, **xaxis_pos)
                self.xaxis2.link_view(self.viewbox2)

            if self.show_yaxis_flatten:
                self.yaxis1 = scene.AxisWidget(
                    orientation='left',
                    axis_label="Signal (uV)",
                    **self.axes_params)
                self.yaxis1.width_max = 40
                self.plot1.add_widget(self.yaxis1, **yaxis_pos)
                self.yaxis1.link_view(self.viewbox1)

                self.yaxis2 = scene.AxisWidget(
                    orientation='left',
                    axis_label="Dispersion (uV)",
                    **self.axes_params)
                self.yaxis2.width_max = 40
                self.plot2.add_widget(self.yaxis2, **yaxis_pos)
                self.yaxis2.link_view(self.viewbox2)

            self.viewbox1.camera.link(self.viewbox2.camera, axis="x")

        elif self.mode == 'geometry':
            plot1_pos = dict(row=0, col=0)
            self.grid.add_widget(widget=self.plot1, **plot1_pos)

            if self.show_xaxis_geometry and self.show_yaxis_geometry:
                xaxis_pos   = dict(row=1, col=1)
                yaxis_pos   = dict(row=0, col=0)
                viewbox_pos = dict(row=0, col=1)
            elif self.show_xaxis_geometry and (not self.show_yaxis_geometry):
                xaxis_pos   = dict(row=1, col=0)
                yaxis_pos   = None
                viewbox_pos = dict(row=0, col=0)
            elif (not self.show_xaxis_geometry) and self.show_yaxis_geometry:
                xaxis_pos   = None
                yaxis_pos   = dict(row=0, col=0)
                viewbox_pos = dict(row=0, col=1)
            else:
                xaxis_pos   = None
                yaxis_pos   = None
                viewbox_pos = dict(row=0, col=0)

            self.viewbox1 = self.plot1.add_view(camera='panzoom', **viewbox_pos)
            self.viewbox2 = self.plot2.add_view(camera='panzoom', **viewbox_pos)

            if self.show_xaxis_geometry:
                self.xaxis1 = scene.AxisWidget(
                    orientation='bottom', axis_label="X (mm)",
                    **self.axes_params)
                self.xaxis1.height_max = 40
                self.plot1.add_widget(self.xaxis1, **xaxis_pos)
                self.xaxis1.link_view(self.viewbox1)

            if self.show_yaxis_geometry:
                self.yaxis1 = scene.AxisWidget(
                    orientation='left', axis_label="Y (mm)",
                    **self.axes_params)
                self.yaxis1.width_max = 40
                self.plot1.add_widget(self.yaxis1, **yaxis_pos)
                self.yaxis1.link_view(self.viewbox1)

        self.curves_individual = []
        self.channel_num_labels = []
        self.region_dict1 = {}
        self.region_dict2 = {}
        self.vline_list1 = []
        self.vline_list2 = []
        #
        self.hline_list1 = []
        self.hline_list2 = []
        self.scalebar_dict1 = {}
        self.scalebar_dict2 = {}
        self.curves_geometry = []
        self.curves_mad_top = []
        self.curves_mad_bottom = []
        # self.curves_mad_fill = []
        self.curves_mad_plot2 = []

        for idx in range(self.params['individual_spikes_num']):
            curve = scene.Line(
                pos=None, width=self.params['linewidth'], parent=self.viewbox1.scene)
            self.curves_individual.append(curve)
        #
        for i, c in enumerate(self.controller.channels):
            # chan is absolut chan
            chan, name = self.controller.channel_indexes_and_names[c]
            itemtxt = scene.Text(
                text=name, 
                parent=self.viewbox1.scene,
                **self.channel_title_params
                )
            self.channel_num_labels.append(itemtxt)
        #
        # self.thresh_line = scene.InfiniteLine(
        #     pos=None, color=self.params['vline_color'].getRgbF())
        # self.thresh_line.visible = False
        regionColor = QT.QColor(self.params['zero_line_color'])
        regionColor.setAlpha(self.alpha)
        regionColor = regionColor.getRgbF()
        vlineColor  = self.params['zero_line_color'].getRgbF()
        hlineColor  = self.params['zero_line_color'].getRgbF()

        for i, c in enumerate(self.controller.channels):
            if i % 2 == 0:
                region = scene.LinearRegion(
                    pos=None, color=regionColor, vertical=True,
                    parent=self.viewbox1.scene)
                region.visible = False
                self.region_dict1[c] = region
                #
                if self.mode == 'flatten':
                    region = scene.LinearRegion(
                        pos=None, color=regionColor, vertical=True,
                        parent=self.viewbox2.scene)
                    region.visible = False
                    self.region_dict2[c] = region
            #
            vline = scene.visuals.Line(
                pos=None, color=vlineColor,
                parent=self.viewbox1.scene
                )
            vline.visible = False
            self.vline_list1.append(vline)
            #
            hline = scene.visuals.Line(
                pos=None, color=hlineColor,
                parent=self.viewbox1.scene
                )
            hline.visible = False
            self.hline_list1.append(hline)
            #
            self.scalebar_dict1[i] = {}
            scalebar = scene.visuals.Axis(
                # axis_label='Time (sec)',
                axis_color=vlineColor, tick_color=vlineColor,
                tick_direction=(0., -1.),
                parent=self.viewbox1.scene,
                **self.scalebar_params)
            scalebar.visible = False
            self.scalebar_dict1[i]['x'] = scalebar
            scalebar = scene.visuals.Axis(
                # axis_label='Signal (uV)',
                axis_color=vlineColor, tick_color=vlineColor,
                parent=self.viewbox1.scene,
                **self.scalebar_params)
            scalebar.visible = False
            self.scalebar_dict1[i]['y'] = scalebar
            #
            if self.mode == 'flatten':
                vline = scene.visuals.Line(
                    pos=None, color=vlineColor,
                    parent=self.viewbox2.scene
                    )
                vline.visible = False
                self.vline_list2.append(vline)
                hline = scene.visuals.Line(
                    pos=None, color=hlineColor,
                    parent=self.viewbox2.scene
                    )
                hline.visible = False
                self.hline_list2.append(hline)
                #
                self.scalebar_dict2[i] = {}
                scalebar = scene.visuals.Axis(
                    # axis_label='Time (sec)',
                    axis_color=vlineColor, tick_color=vlineColor,
                    tick_direction=(0., -1.),
                    parent=self.viewbox2.scene,
                    **self.scalebar_params)
                scalebar.visible = False
                self.scalebar_dict2[i]['x'] = scalebar
                scalebar = scene.visuals.Axis(
                    # axis_label='Dispersion (uV)',
                    axis_color=vlineColor, tick_color=vlineColor,
                    parent=self.viewbox2.scene,
                    **self.scalebar_params)
                scalebar.visible = False
                self.scalebar_dict2[i]['y'] = scalebar

        for k in self.controller.positive_cluster_labels:
            self.add_blank_curve(k)

        if self.mode == 'flatten':
            n_left, n_right = self.controller.get_waveform_left_right()
            width = n_right - n_left
            max_num_points = int(self.params['max_num_points'] / self.controller.nb_channel)
            ds_ratio = width // max_num_points + 1

            if ds_ratio > 1:
                width = width // ds_ratio
                n_left = n_left // ds_ratio
                n_right = n_right // ds_ratio

            self.xvect = np.arange(width * len(self.controller.channels))
            self.xvect = ds_ratio * (self.xvect + n_left) / self.sample_rate
            #
            self.recalc_x_range()
            self.recalc_y_range()
            self.viewbox1.camera.set_range(x=self._x_range, y=self._y1_range, margin=0.)
            self.viewbox2.camera.set_range(x=self._x_range, y=self._y2_range, margin=0.)
        elif self.mode == 'geometry':
            chan_grp = self.controller.chan_grp
            channel_group = self.controller.dataio.channel_groups[chan_grp]
            #
            if channel_group['geometry'] is None:
                print('no geometry')
                self.xvect = None
            else:
                n_left, n_right = self.controller.get_waveform_left_right()
                width = n_right - n_left
                nb_channel = self.controller.nb_channel
                self.xvect = np.zeros((nb_channel, width), dtype='float32')
                for i, chan in enumerate(channel_group['channels']):
                    # x, y = channel_group['geometry'][chan]
                    x = self.arr_geometry[i, 0]
                    self.xvect[i, :] = np.linspace(
                        x - self.espx, x + self.espx, num=width)
                self.recalc_x_range()
                self.recalc_y_range()
                self.viewbox1.camera.set_range(
                    x=self._x_range, y=self._y1_range, margin=0.)
        
        self.enableRefresh()

        return

    def _refresh(self, keep_range=False):
        #
        if LOGGING: logger.info(f'Starting _refresh...')
        n_selected = np.sum(self.controller.spike_selection)
        
        if self.params['show_only_selected_cluster'] and n_selected == 1:
            cluster_visible = {
                k: False for k in self.controller.positive_cluster_labels}
            ind, = np.nonzero(self.controller.spike_selection)
            ind = ind[0]
            k = self.controller.spikes[ind]['cluster_label']
            cluster_visible[k] = True
        else:
            cluster_visible = self.controller.cluster_visible
        
        if self.mode == 'flatten':
            self.refresh_mode_flatten(cluster_visible, keep_range)
        elif self.mode == 'geometry':
            self.refresh_mode_geometry(cluster_visible, keep_range)
        
        self._refresh_individual(n_selected)
        if LOGGING: logger.info(f'Finished ._refresh...')

    def refresh_mode_flatten(self, cluster_visible, keep_range):
        if LOGGING: logger.info(f'Starting _refresh_mode_flatten...')
        
        '''rect1 = self.viewbox1.camera.get_state()['rect']

        if self._x_range is not None and keep_range:
            self._x_range = (rect1.left, rect1.right)
            self._y1_range = (rect1.bottom, rect1.top)
            rect2 = self.viewbox2.camera.get_state()['rect']
            self._y2_range = (rect2.bottom, rect2.top)'''

        n_left, n_right = self.controller.get_waveform_left_right()
        width = n_right - n_left

        max_num_points = int(self.params['max_num_points'] / self.controller.nb_channel)
        ds_ratio = width // max_num_points + 1
        if ds_ratio > 1:
            width = width // ds_ratio
            n_left = n_left // ds_ratio
            n_right = n_right // ds_ratio

        # in flatten mode, no transforms applied to y
        y_center = (self.wf_max + self.wf_min) / 2
        y_domain_length = self.wf_max - self.wf_min
        if y_domain_length > 0:
            y_domain = (self.wf_min, self.wf_max)
        else:
            y_domain_length = 2
            y_domain = (-1, 1)
        y_length = y_domain_length
        y_start, y_stop = y_domain[0], y_domain[1]
        y_offset = y_center - 1.1 * y_length / 2
        # pdb.set_trace()
        for i, c in enumerate(self.controller.channels):
            if self.params['plot_limit_for_flatten']:
                if i % 2 == 0:
                    # region_pos = [width * i, width * (i + 1) - 1)]
                    region_pos = (
                        ds_ratio * (width * i + n_left) / self.sample_rate,
                        ds_ratio * (width * (i + 1) + n_left - 1) / self.sample_rate)
                    self.region_dict1[c].set_data(pos=region_pos)
                    self.region_dict1[c].visible = True
                    self.region_dict2[c].set_data(pos=region_pos)
                    self.region_dict2[c].visible = True
            else:
                if i % 2 == 0:
                    self.region_dict1[c].visible = False
                    self.region_dict2[c].visible = False
            if self.params['plot_zero_vline']:
                # vline_pos = -n_left + width*i
                xpos = ds_ratio * width * i / self.sample_rate
                vline_pos = (
                    (xpos, y_start),
                    (xpos, y_stop)
                    )
                self.vline_list1[i].set_data(pos=vline_pos)
                self.vline_list1[i].visible = True
                self.vline_list2[i].set_data(pos=vline_pos)
                self.vline_list2[i].visible = True
            else:
                self.vline_list1[i].visible = False
                self.vline_list2[i].visible = False

            if self.params['show_scalebar']:
                # in flatten mode, x is offset but not scaled
                x_center = ds_ratio * width * i / self.sample_rate
                x_domain = (
                    0.9 * ds_ratio * n_left / self.sample_rate,
                    0.9 * ds_ratio * n_right / self.sample_rate)
                x_start = x_center + x_domain[0]
                x_stop = x_center + x_domain[1]
                x_length = x_stop - x_start
                #
                ##
                # x scalebar
                ##
                start_pos = (x_start, y_offset)
                end_pos = (x_stop, y_offset)
                self.scalebar_dict1[i]['x'].pos = (start_pos, end_pos)
                self.scalebar_dict1[i]['x'].domain = x_domain
                self.scalebar_dict1[i]['x'].visible = True
                self.scalebar_dict2[i]['x'].pos = (start_pos, end_pos)
                self.scalebar_dict2[i]['x'].domain = x_domain
                self.scalebar_dict2[i]['x'].visible = True
                '''##
                # y scalebar
                ##
                x_offset = x_center - 1.1 * x_length / 2
                start_pos = (x_offset, y_start)
                end_pos = (x_offset, y_stop)
                #
                self.scalebar_dict1[i]['y'].pos = (start_pos, end_pos)
                self.scalebar_dict1[i]['y'].domain = y_domain
                self.scalebar_dict1[i]['y'].visible = True'''

        if self.params['show_channel_num']:
            for i, itemtext in enumerate(self.channel_num_labels):
                itemtext.pos = (
                    ds_ratio * (width * i + n_left + width / 2) / self.sample_rate,
                    self._y1_range[1] * 0.9)
                itemtext.visible = True
        else:
            for itemtext in self.channel_num_labels:
                itemtext.visible = False

        if self.params['summary_statistics'] == 'median/mad':
            key1, key2 = 'median', 'mad'
            zero_centroids = False
        elif self.params['summary_statistics'] == 'mean/std':
            key1, key2 = 'mean', 'std'
            zero_centroids = False
        elif self.params['summary_statistics'] == 'none':
            key1, key2 = 'mean', 'std'
            zero_centroids = True

        for idx, k in enumerate(self.controller.positive_cluster_labels):
            v = cluster_visible[k]
            if zero_centroids or (not v):
                self.curves_geometry[idx].visible = False
                self.curves_mad_top[idx].visible = False
                self.curves_mad_bottom[idx].visible = False
                # self.curves_mad_fill[idx].visible = False
                self.curves_mad_plot2[idx].visible = False
                continue
            #
            #
            wf0, chans = self.controller.get_waveform_centroid(
                k, key1, channels=self.controller.channels)
            if wf0 is None: continue
            if ds_ratio > 1:
                wf0 = wf0[::ds_ratio, :]
                
            wf0 = wf0.T.flatten()

            make_visible = (not zero_centroids) and (not wf0.sum() == 0)
            mad, chans = self.controller.get_waveform_centroid(
                k, key2, channels=self.controller.channels)
            if mad is not None:
                if ds_ratio > 1:
                    mad = mad[::ds_ratio, :]
            xy = np.concatenate((self.xvect[:, None], wf0[:, None],), axis=1)

            self.curves_geometry[idx].set_data(
                pos=xy,
                # color=color
                )
            self.curves_geometry[idx].visible = make_visible

            if mad is not None:
                mad = mad.T.flatten()
                make_visible = (not zero_centroids) and (not np.all(mad == 1))
                # plot1
                if self.params['shade_dispersion']:
                    if make_visible:
                        xy = np.concatenate((self.xvect[:, None], (wf0 + mad)[:, None],), axis=1)
                        self.curves_mad_top[idx].set_data(
                            pos=xy,
                            # color=color
                            )
                        self.curves_mad_top[idx].visible = True
                        xy = np.concatenate((self.xvect[:, None], (wf0 - mad)[:, None],), axis=1)
                        self.curves_mad_bottom[idx].set_data(
                            pos=xy,
                            # color=color
                            )
                        self.curves_mad_bottom[idx].visible = True
                        # self.curves_mad_fill[idx].setCurves(
                        #     curve1=self.curves_mad_top[idx],
                        #     curve2=self.curves_mad_bottom[idx])
                    else:
                        self.curves_mad_top[idx].visible = False
                        self.curves_mad_bottom[idx].visible = False
                # plot2
                if make_visible:
                    xy = np.concatenate((self.xvect[:, None], mad[:, None],), axis=1)
                    self.curves_mad_plot2[idx].set_data(
                        pos=xy,
                        # color=color
                        )
                    self.curves_mad_plot2[idx].visible = True
                else:
                    self.curves_mad_plot2[idx].visible = False

        if LOGGING: logger.info(f'Finished _refresh_mode_flatten...')

    def y_gain(self):
        return self.factor_y * self.delta_y * self.params['y_scaling_factor']

    def refresh_mode_geometry(self, cluster_visible, keep_range):
        if LOGGING: logger.info(f'Starting _refresh_mode_geometry...')

        '''if self._x_range is not None and keep_range:
            rect1 = self.viewbox1.camera.get_state()['rect']
            self._x_range = (rect1.left, rect1.right)
            self._y1_range = (rect1.bottom, rect1.top)'''

        if self.xvect is None:
            return

        n_left, n_right = self.controller.get_waveform_left_right()
        if n_left is None:
            return

        width = n_right - n_left
        
        if width != self.xvect.shape[1]:
            self.initialize_plot()

        if self.params['summary_statistics'] == 'median/mad':
            key1, key2 = 'median', 'mad'
            zero_centroids = False
        elif self.params['summary_statistics'] == 'mean/std':
            key1, key2 = 'mean', 'std'
            zero_centroids = False
        elif self.params['summary_statistics'] == 'none':
            key1, key2 = 'mean', 'std'
            zero_centroids = True

        max_num_points = int(self.params['max_num_points'] / self.controller.nb_channel)
        ds_ratio = width // max_num_points + 1

        if ds_ratio > 1:
            width = width // ds_ratio
            n_left = n_left // ds_ratio
            n_right = n_right // ds_ratio

        for i, c in enumerate(self.controller.channels):
            if self.params['plot_zero_vline'] or self.params['plot_zero_hline'] or self.params['show_scalebar']:
                x_center, y_center = self.arr_geometry[i, :]
                x_start, x_stop = self.xvect[i, 0], self.xvect[i, -1]
                x_length = x_stop - x_start
                #
                y_domain_length = self.wf_max - self.wf_min
                if y_domain_length > 0:
                    y_domain = (- y_domain_length / 2, y_domain_length / 2)
                else:
                    y_domain_length = 2
                    y_domain = (-1, 1)
                #
                y_length = y_domain_length * self.y_gain()
                y_start = y_center + y_domain[0] * self.y_gain()
                y_stop = y_center + y_domain[1] * self.y_gain()
            
            if self.params['plot_zero_vline']:
                xpos = self.xvect[i, int(- ds_ratio * n_left)]
                vline_pos = (
                    (xpos, y_start),
                    (xpos, y_stop)
                    )
                self.vline_list1[i].set_data(pos=vline_pos)
                self.vline_list1[i].visible = True
            else:
                self.vline_list1[i].visible = False

            if self.params['plot_zero_hline']:
                ypos = (y_start + y_stop) / 2
                hline_pos = (
                    (x_start, ypos),
                    (x_stop, ypos)
                    )
                self.hline_list1[i].set_data(pos=hline_pos)
                self.hline_list1[i].visible = True

            if self.params['show_scalebar']:
                ##
                # x scalebar
                ##
                y_offset = y_center - 1.1 * y_length / 2
                start_pos = (x_start, y_offset)
                end_pos = (x_stop, y_offset)
                self.scalebar_dict1[i]['x'].pos = (start_pos, end_pos)
                self.scalebar_dict1[i]['x'].domain = (
                    ds_ratio * n_left / self.sample_rate,
                    ds_ratio * n_right / self.sample_rate)
                self.scalebar_dict1[i]['x'].visible = True
                ##
                # y scalebar
                ##
                x_offset = x_center - 1.1 * x_length / 2
                start_pos = (x_offset, y_start)
                end_pos = (x_offset, y_stop)
                #
                self.scalebar_dict1[i]['y'].pos = (start_pos, end_pos)
                self.scalebar_dict1[i]['y'].domain = y_domain
                self.scalebar_dict1[i]['y'].visible = True
            
            '''else:
                self.scalebar_dict1[i]['x'].visible = False
                self.scalebar_dict1[i]['y'].visible = False
            self.scalebar_dict2[i]['x'].visible = False
            self.scalebar_dict2[i]['y'].visible = False'''

        for idx, k in enumerate(self.controller.positive_cluster_labels):
            '''
            self.curves_mad_top[idx].visible = False
            self.curves_mad_bottom[idx].visible = False
            # self.curves_mad_fill[idx].visible = False
            self.curves_mad_plot2[idx].visible = False
            '''
            v = cluster_visible[k]
            if (not v) or zero_centroids:
                self.curves_geometry[idx].visible = False
                continue
            # print(f'cluster_visible idx, (k, v) {idx}, ({k}, {v})')
            wf, chans = self.controller.get_waveform_centroid(k, key1, sparse=False)
            
            if wf is None: continue
            if ds_ratio > 1:
                wf = wf[::ds_ratio, :]

            ypos = self.arr_geometry[chans, 1]
            
            wf = wf * self.y_gain() + ypos[None, :]
            #wf[0,:] = np.nan
            
            connect = np.ones(wf.shape, dtype='bool')
            connect[0, :] = 0
            connect[-1, :] = 0

            if ds_ratio > 1:
                xvect = self.xvect[chans, ::ds_ratio]
            else:
                xvect = self.xvect[chans, :]

            # color = self.controller.qcolors.get(k, QT.QColor( 'white')).getRgbF()
            
            if zero_centroids:
                self.curves_geometry[idx].visible = False
            else:
                xy = np.concatenate((xvect.flatten()[:, None], wf.T.flatten()[:, None]), axis=1)
                self.curves_geometry[idx].set_data(
                    pos=xy,
                    # color=color,
                    connect=connect.T.flatten())
                self.curves_geometry[idx].visible = True
            
        if self.params['show_channel_num']:
            for i, itemtext in enumerate(self.channel_num_labels):
                x, y = self.arr_geometry[i, : ]
                itemtext.pos = (x, y + 1.1 * self.delta_y / 2)
                itemtext.visible = True
        else:
            for itemtext in self.channel_num_labels:
                itemtext.visible = False
                
        if LOGGING: logger.info(f'Finished _refresh_mode_geometry...')
    
    def on_spike_selection_changed(self):
        if self.params['plot_individual_spikes'] == 'selected':
            self._refresh()

    def _refresh_individual(self, n_selected):
        if LOGGING: logger.info('Starting _refresh_individual')
        # print('Starting _refresh_individual')
        #TODO peak the selected peak if only one
        if self.params['plot_individual_spikes'] == 'none':
            if LOGGING: logger.info('Exited _refresh_individual (none)')
            return
        elif self.params['plot_individual_spikes'] == 'selected':
            if n_selected < 1:
                if LOGGING: logger.info('Exited _refresh_one_spike on (not enough selected)')
                return
            else:
                max_n_spikes = self.params['individual_spikes_num']
                selected = np.flatnonzero(self.controller.spike_selection).tolist()
                selected = selected[:max_n_spikes]
        elif self.params['plot_individual_spikes'] == 'last':
            max_n_spikes = self.params['individual_spikes_num']
            selected = slice(- max_n_spikes, None)
        else:
            return
        cluster_labels = self.controller.spikes[selected]['cluster_label']
        n_left, n_right = self.controller.get_waveform_left_right()
        all_wf = self.controller.dataio.get_some_waveforms(
            chan_grp=self.controller.chan_grp, peaks_index=selected)
        n_spikes = all_wf.shape[0]
        #
        max_num_points = int(self.params['max_num_points'] / self.controller.nb_channel)
        width = (n_right - n_left)
        ds_ratio =  width // max_num_points + 1
        if ds_ratio > 1:
            n_left = n_left // ds_ratio
        #
        # print(f"refresh inidvidual, all_wf.shape[1] = {all_wf.shape[1]}")
        # print(f"refresh inidvidual, width = {width}")
        if all_wf.shape[1] == width:
            #this avoid border bugs
            self.last_individual_wf = all_wf
            for idx in range(n_spikes):
                curve = self.curves_individual[idx]
                if ds_ratio > 1:
                    wf = all_wf[idx, ::ds_ratio, :]
                else:
                    wf = all_wf[idx, :, :]
                # if wf.sum() == 0:
                #     print(f"wf.sum() = {wf.sum()}")
                #     continue
                k = cluster_labels[idx]
                color = self.controller.qcolors.get(k, QT.QColor('white')).getRgbF()
                if self.mode == 'flatten':
                    '''if self._common_channels_flat is None:
                        curve.visible = False
                        return
                    wf = wf[:, self._common_channels_flat].T.flatten()'''
                    wf = wf.T.flatten()
                    xvect = np.arange(wf.size)
                    xvect = ds_ratio * (xvect + n_left) / self.sample_rate
                    xy = np.concatenate((xvect[:, None], wf[:, None],), axis=1)
                    curve.set_data(pos=xy, color=color)
                    curve.visible = True
                elif self.mode == 'geometry':
                    ypos = self.arr_geometry[:, 1]
                    wf = wf * self.y_gain() + ypos[None, :]
                    connect = np.ones(wf.shape, dtype='bool')
                    connect[0, :] = 0
                    connect[-1, :] = 0
                    if ds_ratio > 1:
                        xvect = self.xvect[:, ::ds_ratio]
                    else:
                        xvect = self.xvect
                    # print(f"refresh inidvidual, factor_y = {self.factor_y}")
                    xy = np.concatenate((xvect.flatten()[:, None], wf.T.flatten()[:, None],), axis=1)
                    curve.set_data(pos=xy, color=color, connect=connect.T.flatten())
                    curve.visible = True
        if n_spikes < max_n_spikes:
            for idx in range(n_spikes, max_n_spikes):
                curve = self.curves_individual[idx]
                curve.visible = False
        if LOGGING: logger.info('Finished _refresh_individual')
