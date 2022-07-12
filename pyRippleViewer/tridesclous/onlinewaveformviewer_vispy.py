from ephyviewer.myqt import QT, QT_LIB
from contextlib import nullcontext
import numpy as np
from pyRippleViewer.tridesclous.base import WidgetBase
import logging
from ephyviewer.base_vispy import MyQtSceneCanvas

LOGGING = False
logger = logging.getLogger(__name__)

from vispy import scene
class WaveformViewerBase(WidgetBase):

    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        # self.lock = Mutex()
        self.lock = nullcontext()
        #~ self.create_settings()
        
        self.create_toolbar()
        self.layout.addWidget(self.toolbar)

        self.sceneCanvas = MyQtSceneCanvas(
            parent=self, keys='interactive', show=True)
        self.layout.addWidget(self.sceneCanvas)
        self.grid = self.sceneCanvas.central_widget.add_grid(margin=0)
        self.plot1 = None
        self.plot2 = None

        self.alpha = 60
        self.initialize_plot()
        
        self.refresh(keep_range=False)
    
    def create_toolbar(self):
        tb = self.toolbar = QT.QToolBar()
        
        #Mode flatten or geometry
        self.combo_mode = QT.QComboBox()
        tb.addWidget(self.combo_mode)
        #self.mode = 'flatten'
        #self.combo_mode.addItems([ 'flatten', 'geometry'])
        self.mode = 'geometry'
        self.combo_mode.addItems([ 'geometry', 'flatten'])
        self.combo_mode.currentIndexChanged.connect(self.on_combo_mode_changed)
        tb.addSeparator()
        
        but = QT.QPushButton('settings')
        but.clicked.connect(self.open_settings)
        tb.addWidget(but)

        but = QT.QPushButton('scale')
        but.clicked.connect(self.zoom_range)
        tb.addWidget(but)

        but = QT.QPushButton('refresh')
        but.clicked.connect(self.refresh)
        tb.addWidget(but)
    
    def gain_zoom(self, factor_ratio):
        self.factor_y *= factor_ratio
        self.refresh(keep_range=True)
    
    def zoom_range(self):
        self._x_range = None
        self._y1_range = None
        self._y2_range = None
        if self.mode=='flatten':
            self.factor_y = 1.
        elif self.mode=='geometry':
            self.factor_y = 0.5
        self.refresh(keep_range=False)
    
    def on_combo_mode_changed(self):
        self.mode = str(self.combo_mode.currentText())
        self.initialize_plot()
        self.refresh(keep_range=False)
    
    def on_params_changed(self, params, changes):
        for param, change, data in changes:
            if change != 'value': continue
            if param.name() == 'flip_bottom_up':
                self.initialize_plot()
            elif param.name() == 'individual_spikes_num':
                self.initialize_plot()
        self.clear_plots()

    def initialize_plot(self):
        if LOGGING: logger.info(f'WaveformViewer.initialize_plot')
        with self.lock:
            self._initialize_plot()
    
    def refresh(self, keep_range=True):
        # if LOGGING: logger.info(f'WaveformViewer.refresh {self.sender()}')
        with self.lock:
            self._refresh(keep_range=keep_range)

    def clear_plots(self):
        with self.lock:
            for curve in self.curves_individual:
                curve.visible = False
            cluster_labels = self.controller.positive_cluster_labels
            for idx, k in enumerate(cluster_labels):
                self.curves_geometry[idx].visible = False
                if self.mode=='flatten':
                    self.curves_mad_top[idx].visible = False
                    self.curves_mad_bottom[idx].visible = False
                    self.curves_mad_plot2[idx].visible = False
        
    def _initialize_plot(self):
        if self.controller.get_waveform_left_right()[0] is None:
            return

        if self.plot1 is not None:
            self.grid.remove_widget(self.plot1)
            self.plot1.parent = None

        self.plot1 = scene.Grid()
        self.viewbox1 = self.plot1.add_view(row=0, col=0, camera='panzoom')
        self.grid.add_widget(widget=self.plot1, row=0, col=0)

        if self.plot2 is not None:
            self.grid.remove_widget(self.plot2)
            self.plot2.parent = None

        self.plot2 = scene.Grid()
        self.viewbox2 = self.plot2.add_view(row=0, col=0, camera='panzoom')

        self.curves_individual = []
        #
        for idx in range(self.params['individual_spikes_num']):
            curve = scene.Line(pos=None, width=1, parent=self.viewbox1.scene)
            self.curves_individual.append(curve)
        #
        self.curves_geometry = []
        #
        cluster_labels = self.controller.positive_cluster_labels
        for k in cluster_labels:
            curve = scene.Line(pos=None, width=2, parent=self.viewbox1.scene)
            self.curves_geometry.append(curve)

        cn = self.controller.channel_indexes_and_names
        self.channel_num_labels = []
        for i, c in enumerate(self.controller.channels):
            # chan is absolut chan
            chan, name = cn[c]
            itemtxt = scene.Text(
                text=name, color='white',
                font_size=12,
                parent=self.viewbox1.scene)
            self.channel_num_labels.append(itemtxt)
        #
        self.thresh_line = scene.InfiniteLine(pos=None, color=self.params['vline_color'].getRgbF())
        self.thresh_line.visible = False
        
        self._common_channels_flat = self.controller.channels

        self.region_dict1 = {}
        self.region_dict2 = {}
        self.vline_list1 = []
        self.vline_list2 = []
        for i, c in enumerate(self.controller.channels):
            if i%2==1:
                region = scene.LinearRegion(pos=None, color=self.params['vline_color'].getRgbF(), vertical=True,
                parent=self.viewbox1.scene)
                region.visible = False
                self.region_dict1[c] = region
                #
                region = scene.LinearRegion(pos=None, color=self.params['vline_color'].getRgbF(), vertical=True,
                parent=self.viewbox2.scene)
                region.visible = False
                self.region_dict2[c] = region
            vline = scene.InfiniteLine(
                pos=None, color=self.params['vline_color'].getRgbF(), vertical=True,
                parent=self.viewbox1.scene
                )
            vline.visible = False
            self.vline_list1.append(vline)
            vline = scene.InfiniteLine(
                pos=None, color=self.params['vline_color'].getRgbF(), vertical=True,
                parent=self.viewbox2.scene
                )
            vline.visible = False
            self.vline_list2.append(vline)

        self.curves_mad_top = []
        self.curves_mad_bottom = []
        # self.curves_mad_fill = []
        self.curves_mad_plot2 = []
        for k in cluster_labels:
            color = self.controller.qcolors[k].getRgbF()
            color2 = QT.QColor(self.controller.qcolors[k])
            color2.setAlpha(self.alpha)
            color2 = color2.getRgbF()
            #
            curve_top = scene.Line(pos=None, color=color, width=1, parent=self.viewbox1.scene)
            self.curves_mad_top.append(curve_top)
            curve_bottom = scene.Line(pos=None, color=color, width=1, parent=self.viewbox1.scene)
            self.curves_mad_bottom.append(curve_bottom)
            # TODO! fillbetween from Polygon
            # fill = pg.FillBetweenItem(curve1=curve_top, curve2=curve_bottom, brush=color2)
            # self.plot1.addItem(fill)
            # self.curves_mad_fill.append(fill)
            curve_p2 = scene.Line(pos=None, width=1, parent=self.viewbox2.scene)
            self.curves_mad_plot2.append(curve_p2)
        if self.mode=='flatten':
            self.grid.add_widget(widget=self.plot2, row=1, col=0)
            self.factor_y = 1.
            for idx, k in enumerate(cluster_labels):
                self.curves_mad_top[idx].visible = True
                self.curves_mad_bottom[idx].visible = True
                self.curves_mad_plot2[idx].visible = True
        elif self.mode=='geometry':
            for idx, k in enumerate(cluster_labels):
                self.curves_mad_top[idx].visible = False
                self.curves_mad_bottom[idx].visible = False
                self.curves_mad_plot2[idx].visible = False
            #
            chan_grp = self.controller.chan_grp
            channel_group = self.controller.dataio.channel_groups[chan_grp]
            #~ print(channel_group['geometry'])
            if channel_group['geometry'] is None:
                print('no geometry')
                self.xvect = None
            else:
                n_left, n_right = self.controller.get_waveform_left_right()
                width = n_right - n_left
                nb_channel = self.controller.nb_channel
                self.xvect = np.zeros((nb_channel, width), dtype='float32')
                self.arr_geometry = []
                for i, chan in enumerate(self.controller.channel_indexes):
                    x, y = channel_group['geometry'][chan]
                    self.arr_geometry.append([x, y])
                self.arr_geometry = np.array(self.arr_geometry, dtype='float64')
                if self.params['flip_bottom_up']:
                    self.arr_geometry[:, 1] *= -1.
                xpos = self.arr_geometry[:,0]
                ypos = self.arr_geometry[:,1]
                if np.unique(xpos).size>1:
                    self.delta_x = np.min(np.diff(np.sort(np.unique(xpos))))
                else:
                    self.delta_x = np.unique(xpos)[0]
                if np.unique(ypos).size>1:
                    self.delta_y = np.min(np.diff(np.sort(np.unique(ypos))))
                else:
                    self.delta_y = max(np.unique(ypos)[0], 1)
                self.factor_y = .3
                if self.delta_x > 0.:
                    #~ espx = self.delta_x/2. *.95
                    espx = self.delta_x/2.5
                else:
                    espx = .5
                for i, chan in enumerate(channel_group['channels']):
                    x, y = channel_group['geometry'][chan]
                    self.xvect[i, :] = np.linspace(x-espx, x+espx, num=width)
        
        self.wf_min, self.wf_max = self.controller.get_min_max_centroids()
        
        self._x_range = None
        self._y1_range = None
        self._y2_range = None
        
        self.sceneCanvas.ygain_zoom.connect(self.gain_zoom)
        self.sceneCanvas.doubleclicked.connect(self.open_settings)
        #~ self.viewBox.xsize_zoom.connect(self.xsize_zoom)    

    def _refresh(self, keep_range=False):
        #
        if LOGGING: logger.info(f'Starting _refresh...')
        n_selected = np.sum(self.controller.spike_selection)
        
        if self.params['show_only_selected_cluster'] and n_selected==1:
            cluster_visible = {
                k: False for k in self.controller.positive_cluster_labels}
            ind, = np.nonzero(self.controller.spike_selection)
            ind = ind[0]
            k = self.controller.spikes[ind]['cluster_label']
            cluster_visible[k] = True
        else:
            cluster_visible = self.controller.cluster_visible
        
        if self.mode=='flatten':
            self.refresh_mode_flatten(cluster_visible, keep_range)
        elif self.mode=='geometry':
            self.refresh_mode_geometry(cluster_visible, keep_range)
        
        self._refresh_individual(n_selected)
        if LOGGING: logger.info(f'Finished ._refresh...')


    def refresh_mode_flatten(self, cluster_visible, keep_range):
        if LOGGING: logger.info(f'Starting _refresh_mode_flatten...')
        if self._x_range is not None and keep_range:
            rect1 = self.viewbox1.camera.get_state()['rect']
            self._x_range = (rect1.left, rect1.right)
            self._y1_range = (rect1.bottom, rect1.top)
            rect2 = self.viewbox2.camera.get_state()['rect']
            self._y2_range = (rect2.bottom, rect2.top)

        if self.controller.spike_index == []:
            return

        #waveforms
        if self.params['metrics']=='median/mad':
            key1, key2 = 'median', 'mad'
            zero_centroids = False
        elif self.params['metrics']=='mean/std':
            key1, key2 = 'mean', 'std'
            zero_centroids = False
        elif self.params['metrics']=='none':
            key1, key2 = 'mean', 'std'
            zero_centroids = True

        nb_channel = self.controller.nb_channel
        n_left, n_right = self.controller.get_waveform_left_right()
        width = n_right - n_left

        max_num_points = int(self.params['max_num_points'] / self.controller.nb_channel)
        ds_ratio = width // max_num_points + 1
        if ds_ratio > 1:
            width = width // ds_ratio
            n_left = n_left // ds_ratio
        
        if self.params['plot_limit_for_flatten']:
            for i, c in enumerate(self.controller.channels):
                if i%2==1:
                    self.region_dict1[c].set_data(pos=[width*i, width*(i+1)-1])
                    self.region_dict1[c].visible = True
                    self.region_dict2[c].set_data(pos=[width*i, width*(i+1)-1])
                    self.region_dict2[c].visible = True
                self.vline_list1[i].set_data(pos=-n_left + width*i)
                self.vline_list1[i].visible = True
                self.vline_list2[i].set_data(pos=-n_left + width*i)
                self.vline_list2[i].visible = True
        else:
            for i, c in enumerate(self.controller.channels):
                if i%2==1:
                    self.region_dict1[c].visible = False
                    self.region_dict2[c].visible = False
                self.vline_list1[i].visible = False
                self.vline_list2[i].visible = False

        if self.params['display_threshold']:
            thresh = self.controller.get_threshold()
            self.thresh_line.set_data(pos=thresh, color=self.params['vline_color'].getRgbF())
            self.thresh_line.visible = True
        else:
            self.thresh_line.visible = False
        
        xvect = None
        for idx, (k, v) in enumerate(cluster_visible.items()):
            if not v:
                if k>=0:
                    self.curves_geometry[idx].visible = False
                    self.curves_mad_top[idx].visible = False
                    self.curves_mad_bottom[idx].visible = False
                    # self.curves_mad_fill[idx].visible = False
                    self.curves_mad_plot2[idx].visible = False
                continue
            color = self.controller.qcolors.get(k, QT.QColor('white')).getRgbF()
            color2 = QT.QColor(self.controller.qcolors[k])
            color2.setAlpha(self.alpha)
            color2 = color2.getRgbF()
            #
            wf0, chans = self.controller.get_waveform_centroid(k, key1, channels=self.controller.channels)
            if wf0 is None: continue
            if ds_ratio > 1:
                wf0 = wf0[::ds_ratio, :]
            if xvect is None:
                xvect = np.arange(wf0.shape[0] * len(self.controller.channels))
            wf0 = wf0.T.flatten()
            mad, chans = self.controller.get_waveform_centroid(k, key2, channels=self.controller.channels)
            if mad is not None:
                if ds_ratio > 1:
                    mad = mad[::ds_ratio, :]
            xy = np.concatenate((xvect[:, None], wf0[:, None],), axis=1)
            self.curves_geometry[idx].set_data(pos=xy, color=color, width=2)
            self.curves_geometry[idx].visible = True
            if self.params['fillbetween'] and mad is not None:
                mad = mad.T.flatten()
                if zero_centroids:
                    self.curves_mad_top[idx].visible = False
                    self.curves_mad_bottom[idx].visible = False
                else:
                    xy = np.concatenate((xvect[:, None], (wf0+mad)[:, None],), axis=1)
                    self.curves_mad_top[idx].set_data(pos=xy, color=color, width=1)
                    self.curves_mad_top[idx].visible = True
                    xy = np.concatenate((xvect[:, None], (wf0-mad)[:, None],), axis=1)
                    self.curves_mad_bottom[idx].set_data(pos=xy, color=color, width=1)
                    self.curves_mad_bottom[idx].visible = True
                # self.curves_mad_fill[idx].setCurves(
                #     curve1=self.curves_mad_top[idx],
                #     curve2=self.curves_mad_bottom[idx])
            if mad is not None:
                if zero_centroids:
                    self.curves_mad_plot2[idx].visible = False
                else:
                    xy = np.concatenate((xvect[:, None], mad[:, None],), axis=1)
                    self.curves_mad_plot2[idx].set_data(pos=xy, color=color, width=1)
                    self.curves_mad_plot2[idx].visible = True
        #
        if self.params['show_channel_num']:
            for i, itemtext in enumerate(self.channel_num_labels):
                itemtext.pos = (width*i, 0)
                itemtext.visible = True
        else:
            for itemtext in self.channel_num_labels:
                itemtext.visible = False
        if self._x_range is None or not keep_range :
            if xvect.size > 0:
                self._x_range = xvect[0], xvect[-1]
                self._y1_range = self.wf_min * 1.1, self.wf_max * 1.1
                self._y2_range = 0., 5.
            self.viewbox1.camera.set_range(
                x=self._x_range, y=self._y1_range, margin=0.)
            self.viewbox2.camera.set_range(
                x=self._x_range, y=self._y2_range, margin=0.)
        if LOGGING: logger.info(f'Finished _refresh_mode_flatten...')

    def refresh_mode_geometry(self, cluster_visible, keep_range):
        if LOGGING: logger.info(f'Starting _refresh_mode_geometry...')
        if self._x_range is not None and keep_range:
            rect = self.viewbox1.camera.get_state()['rect']
            self._x_range = (rect.left, rect.right)
            self._y1_range = (rect.bottom, rect.top)

        for i, c in enumerate(self.controller.channels):
            if i%2==1:
                self.region_dict1[c].visible = False
                self.region_dict2[c].visible = False
            self.vline_list1[i].visible = False
            self.vline_list2[i].visible = False

        if self.xvect is None:
            return

        n_left, n_right = self.controller.get_waveform_left_right()
        if n_left is None:
            return
        width = n_right - n_left
        
        if width != self.xvect.shape[1]:
            self.initialize_plot()

        if self.params['metrics']=='median/mad':
            key1, key2 = 'median', 'mad'
            zero_centroids = False
        elif self.params['metrics']=='mean/std':
            key1, key2 = 'mean', 'std'
            zero_centroids = False
        elif self.params['metrics']=='none':
            key1, key2 = 'mean', 'std'
            zero_centroids = True

        max_num_points = int(self.params['max_num_points'] / self.controller.nb_channel)
        ds_ratio = width // max_num_points + 1
        for idx, k in enumerate(self.controller.positive_cluster_labels):
            self.curves_mad_top[idx].visible = False
            self.curves_mad_bottom[idx].visible = False
            # self.curves_mad_fill[idx].visible = False
            self.curves_mad_plot2[idx].visible = False

        for idx, (k, v) in enumerate(cluster_visible.items()):
            if not v:
                if k>=0:
                    self.curves_geometry[idx].visible = False
                continue
            # print(f'cluster_visible idx, (k, v) {idx}, ({k}, {v})')
            wf, chans = self.controller.get_waveform_centroid(k, key1, sparse=False)
            
            if wf is None: continue
            if ds_ratio > 1:
                wf = wf[::ds_ratio, :]

            ypos = self.arr_geometry[chans,1]
            
            wf = wf * self.factor_y * self.delta_y + ypos[None, :]
            #wf[0,:] = np.nan
            
            connect = np.ones(wf.shape, dtype='bool')
            connect[0, :] = 0
            connect[-1, :] = 0
            if ds_ratio > 1:
                xvect = self.xvect[chans, ::ds_ratio]
            else:
                xvect = self.xvect[chans, :]

            color = self.controller.qcolors.get(k, QT.QColor( 'white')).getRgbF()
            
            if zero_centroids:
                self.curves_geometry[idx].visible = False
            else:
                xy=np.concatenate((xvect.flatten()[:, None], wf.T.flatten()[:, None]), axis=1)
                self.curves_geometry[idx].set_data(pos=xy,color=color, width=2, connect=connect.T.flatten())
                self.curves_geometry[idx].visible = True
            
        if self.params['show_channel_num']:
            for i, itemtext in enumerate(self.channel_num_labels):
                x, y = self.arr_geometry[i, : ]
                itemtext.pos = (x, y)
                itemtext.visible = True
        else:
            for itemtext in self.channel_num_labels:
                itemtext.visible = False
        #~ if self._x_range is None:
        if self._x_range is None or not keep_range:
            self._x_range = np.min(self.xvect), np.max(self.xvect)
            self._y1_range = np.min(self.arr_geometry[:,1])-self.delta_y*2, np.max(self.arr_geometry[:,1])+self.delta_y*2
            self.viewbox1.camera.set_range(
                x=self._x_range, y=self._y1_range, margin=0.)
        if LOGGING: logger.info(f'Finished _refresh_mode_geometry...')
    
    def _refresh_individual(self, n_selected):
        if LOGGING: logger.info('Starting _refresh_individual')
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
            chan_grp=self.controller.chan_grp,
            peaks_index=selected)
        n_spikes = all_wf.shape[0]
        #
        max_num_points = int(self.params['max_num_points'] / self.controller.nb_channel)
        ds_ratio = (n_right-n_left) // max_num_points + 1
        #
        if all_wf.shape[1]==(n_right-n_left):
            #this avoid border bugs
            for idx in range(n_spikes):
                curve = self.curves_individual[idx]
                if ds_ratio > 1:
                    wf = all_wf[idx, ::ds_ratio, :]
                else:
                    wf = all_wf[idx, :, :]
                k = cluster_labels[idx]
                color = self.controller.qcolors.get(k, QT.QColor('white')).getRgbF()
                if self.mode=='flatten':
                    if self._common_channels_flat is None:
                        curve.visible = False
                        return
                    wf = wf[:, self._common_channels_flat].T.flatten()
                    xvect = np.arange(wf.size)
                    xy = np.concatenate((xvect[:, None], wf[:, None],), axis=1)
                    curve.set_data(pos=xy, color=color)
                    curve.visible = True
                elif self.mode=='geometry':
                    ypos = self.arr_geometry[:,1]
                    wf = wf * self.factor_y * self.delta_y + ypos[None, :]
                    connect = np.ones(wf.shape, dtype='bool')
                    connect[0, :] = 0
                    connect[-1, :] = 0
                    if ds_ratio > 1:
                        xvect = self.xvect[:, ::ds_ratio]
                    else:
                        xvect = self.xvect
                    xy = np.concatenate((xvect.flatten()[:, None], wf.T.flatten()[:, None],), axis=1)
                    curve.set_data(pos=xy, color=color, connect=connect.T.flatten())
                    curve.visible = True
        if n_spikes < max_n_spikes:
            for idx in range(n_spikes, max_n_spikes):
                curve = self.curves_individual[idx]
                curve.visible = False
        if LOGGING: logger.info('Finished _refresh_individual')

    def on_spike_selection_changed(self):
        #~ n_selected = np.sum(self.controller.spike_selection)
        #~ self._refresh_one_spike(n_selected)
        if LOGGING: logger.info('Starting on_spike_selection_changed')
        # self.refresh(keep_range=True)
        if LOGGING: logger.info('Finished on_spike_selection_changed')

class RippleWaveformViewer(WaveformViewerBase):
    """
    **Waveform viewer** is undoubtedly the view to inspect waveforms.
    
    Note that in some aspect **Waveform hist viewer** can be a better firend.
    
    All centroid (median or mean) of visible cluster are plotted here.
    
    2 main modes:
      * **geometry** waveforms are organized with 2d geometry given by PRB file.
      * **flatten** each chunk of each channel is put side by side in channel order
        than it can be ploted in 1d. The bottom view is th mad. On good cluster the mad
        must as close as possible from the value 1 because 1 is the normalized noise.
    
    The **geometry** mode is more intuitive and help users about spatial
    information. But the  **flatten**  mode is really important because is give information 
    about the variance (mad or std) for each point and about peak alignement.
    
    The centoid is dfine by median+mad but you can also check with mean+std.
    For healthy cluster it should more or less the same.
    
    Important for zooming:
      *  **geometry** : zoomXY geometry = right click, move = left click and mouse wheel = zoom waveforms
      * **flatten**: zoomXY = right click and move = left click
    
    
    Settings:
      * **plot_selected_spike**: superimposed one slected peak on centroid
      * **show_only_selected_cluster**: this auto hide all cluster except the one of selected spike
      * **plot_limit_for_flatten**: for flatten mode this plot line for delimiting channels.
        Plotting is important but it slow down the zoom.
      * **metrics**: choose median+mad or mean+std.
      * *show_channel_num**: what could it be ?
      * **flip_bottom_up**: in geometry this flip bottom up the channel geometry.
      * **display_threshold**: what could it be ?
    """
    _params = [
        {'name': 'max_num_points', 'type' :'int', 'value' : 16000, 'limits':[2000, np.inf]},
        {'name': 'plot_individual_spikes', 'type': 'list', 'value': 'last', 'values': ['last', 'selected', 'none']},
        {'name': 'individual_spikes_num', 'type' :'int', 'value' : 5, 'limits':[1, np.inf]},
        {'name': 'show_only_selected_cluster', 'type': 'bool', 'value': False},
        {'name': 'plot_limit_for_flatten', 'type': 'bool', 'value': True},
        {'name': 'metrics', 'type': 'list', 'value': 'none', 'values': ['median/mad', 'none'] },
        {'name': 'fillbetween', 'type': 'bool', 'value': True},
        {'name': 'show_channel_num', 'type': 'bool', 'value': True},
        {'name': 'flip_bottom_up', 'type': 'bool', 'value': False},
        {'name': 'display_threshold', 'type': 'bool', 'value' : False},
        {'name': 'vline_color', 'type': 'color', 'value': '#FFFFFFAA'},
        {'name': 'sparse_display', 'type': 'bool', 'value' : False },
        ]