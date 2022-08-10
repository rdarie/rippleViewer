from ephyviewer.myqt import QT, QT_LIB
import pyqtgraph as pg

import numpy as np
from pyqtgraph.util.mutex import Mutex
from pyRippleViewer.tridesclous.base import WidgetBase
import logging

LOGGING = True
logger = logging.getLogger(__name__)

class MyViewBox(pg.ViewBox):
    doubleclicked = QT.pyqtSignal()
    gain_zoom = QT.pyqtSignal(float)
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        #~ self.disableAutoRange()
    def mouseClickEvent(self, ev):
        ev.accept()
    def mouseDoubleClickEvent(self, ev):
        self.doubleclicked.emit()
        ev.accept()
    #~ def mouseDragEvent(self, ev):
        #~ ev.ignore()
    def wheelEvent(self, ev, axis=None):
        if ev.modifiers() == QT.Qt.ControlModifier:
            z = 10 if ev.delta()>0 else 1/10.
        else:
            z = 1.3 if ev.delta()>0 else 1/1.3
        self.gain_zoom.emit(z)
        ev.accept()



class WaveformViewerBase(WidgetBase):
    #base for both WaveformViewer (Catalogue) and PeelerWaveformViewer
    

    
    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        self.lock = Mutex()
        #~ self.create_settings()
        
        self.create_toolbar()
        self.layout.addWidget(self.toolbar)

        self.graphicsview = pg.GraphicsView()
        self.layout.addWidget(self.graphicsview)
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
            # if param.name() == 'flip_bottom_up':
            #     self.initialize_plot()
            if param.name() == 'individual_spikes_num':
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
                curve.setData([], [])
            cluster_labels = self.controller.positive_cluster_labels
            for idx, k in enumerate(cluster_labels):
                self.curves_geometry[idx].setData([], [])
                if self.mode=='flatten':
                    self.curves_mad_top[idx].setData([], [])
                    self.curves_mad_bottom[idx].setData([], [])
                    self.curves_mad_plot2[idx].setData([], [])
        
    def _initialize_plot(self):
        if self.controller.get_waveform_left_right()[0] is None:
            return
            
        self.viewBox1 = MyViewBox()
        self.viewBox1.disableAutoRange()

        grid = pg.GraphicsLayout(border=(100,100,100))
        self.graphicsview.setCentralItem(grid)
        
        self.plot1 = grid.addPlot(row=0, col=0, rowspan=2, viewBox=self.viewBox1)
        self.plot1.hideButtons()
        # (left, top, right, bottom)
        self.plot1.showAxes((False, False, False, False), showValues=False, size=False)
        # print(f'self.plot1 = {self.plot1}')
        self.curves_individual = []
        #
        for idx in range(self.params['individual_spikes_num']):
            curve = pg.PlotCurveItem(
                [], [], 
                downsampleMethod='peak', downsample=1,
                autoDownsample=False, clipToView=True, antialias=False,
                pen=pg.mkPen(QT.QColor('white'), width=self.params['line_width']), connect='finite')
            self.plot1.addItem(curve)
            self.curves_individual.append(curve)
        #
        self.curves_geometry = []
        #
        cluster_labels = self.controller.positive_cluster_labels
        for k in cluster_labels:
            curve = pg.PlotCurveItem(
                [], [], downsampleMethod='peak', downsample=1,
                autoDownsample=False, clipToView=True, antialias=False,
                pen=pg.mkPen(self.controller.qcolors[k], width=self.params['line_width']), connect='finite')
            self.plot1.addItem(curve)
            self.curves_geometry.append(curve)
        cn = self.controller.channel_indexes_and_names
        self.channel_num_labels = []
        for i, c in enumerate(self.controller.channels):
            # chan i sabsolut chan
            chan, name = cn[c]
            itemtxt = pg.TextItem('{}: {}'.format(i, name), anchor=(.5,.5), color='#FFFF00')
            itemtxt.setFont(QT.QFont('', pointSize=12))
            itemtxt.setPos(0, 0)
            itemtxt.hide()
            self.plot1.addItem(itemtxt)
            self.channel_num_labels.append(itemtxt)
        if self.mode=='flatten':
            self.is_span_added = False
            grid.nextRow()
            grid.nextRow()
            self.viewBox2 = MyViewBox()
            self.viewBox2.disableAutoRange()
            self.plot2 = grid.addPlot(row=2, col=0, rowspan=1, viewBox=self.viewBox2)
            self.plot2.hideButtons()
            self.plot2.showAxes((False, False, False, False), showValues=False, size=False)
            self.viewBox2.setXLink(self.viewBox1)
            self.factor_y = 1.
            
            self._common_channels_flat = None
            self.curves_mad_top = []
            self.curves_mad_bottom = []
            self.curves_mad_fill = []
            self.curves_mad_plot2 = []
            for k in cluster_labels:
                color = self.controller.qcolors[k]
                color2 = QT.QColor(self.controller.qcolors[k])
                color2.setAlpha(self.alpha)
                curve_top = pg.PlotCurveItem(
                    [], [], downsampleMethod='peak', downsample=1,
                    autoDownsample=False, clipToView=True, antialias=False,
                    pen=pg.mkPen(color, width=self.params['line_width']), connect='finite')
                self.plot1.addItem(curve_top)
                self.curves_mad_top.append(curve_top)
                curve_bottom = pg.PlotCurveItem(
                    [], [], downsampleMethod='peak', downsample=1,
                    autoDownsample=False, clipToView=True, antialias=False,
                    pen=pg.mkPen(color, width=self.params['line_width']), connect='finite')
                self.plot1.addItem(curve_bottom)
                self.curves_mad_bottom.append(curve_bottom)
                fill = pg.FillBetweenItem(curve1=curve_top, curve2=curve_bottom, brush=color2)
                self.plot1.addItem(fill)
                self.curves_mad_fill.append(fill)
                curve_p2 = pg.PlotCurveItem(
                    [], [], downsampleMethod='peak', downsample=1,
                    autoDownsample=False, clipToView=True, antialias=False,
                    pen=pg.mkPen(color, width=self.params['line_width']), connect='finite')
                self.plot2.addItem(curve_p2)
                self.curves_mad_plot2.append(curve_p2)
        elif self.mode=='geometry':
            self.plot2 = None
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
                
                #~ self.xvect = np.zeros(shape[0]*shape[1], dtype='float32')
                #~ self.xvect = np.zeros((shape[1], shape[0]), dtype='float32')
                self.xvect = np.zeros((nb_channel, width), dtype='float32')

                self.arr_geometry = []
                for i, chan in enumerate(self.controller.channel_indexes):
                    x, y = channel_group['geometry'][chan]
                    self.arr_geometry.append([x, y])
                self.arr_geometry = np.array(self.arr_geometry, dtype='float64')
                
                # if self.params['flip_bottom_up']:
                #     self.arr_geometry[:, 1] *= -1.
                
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
        
        self.viewBox1.gain_zoom.connect(self.gain_zoom)
        self.viewBox1.doubleclicked.connect(self.open_settings)

        #~ self.viewBox.xsize_zoom.connect(self.xsize_zoom)    

    def _refresh(self, keep_range=False):
        #
        if not hasattr(self, 'viewBox1'):
            return
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
    
    def addSpan(self, plot, width, common_channels, n_left):
        white = pg.mkColor(255, 255, 255, 20)
        #~ for i in range(nb_channel):
        region_list = []
        vline_list = []
        for i, c in enumerate(common_channels):
            if i%2==1:
                region = pg.LinearRegionItem([width*i, width*(i+1)-1], movable = False, brush=white)
                plot.addItem(region, ignoreBounds=True)
                region_list.append(region)
                for l in region.lines:
                    l.setPen(white, width=self.params['line_width'])
            vline = pg.InfiniteLine(pos = -n_left + width*i, angle=90, movable=False, pen=pg.mkPen('w'))
            plot.addItem(vline)
            vline_list.append(vline)
        return region_list, vline_list

    def refresh_mode_flatten(self, cluster_visible, keep_range):
        if LOGGING: logger.info(f'Starting _refresh_mode_flatten...')
        if self._x_range is not None and keep_range:
            #this may change with pyqtgraph
            self._x_range = tuple(self.viewBox1.state['viewRange'][0])
            self._y1_range = tuple(self.viewBox1.state['viewRange'][1])
            self._y2_range = tuple(self.viewBox2.state['viewRange'][1])
        '''
        self.plot1.clear()
        self.plot2.clear()

        self.plot1.addItem(self.curve_one_waveform)
        for idx in range(self.params['last_few_spikes_num']):
            self.plot1.addItem(self.curves_last_few[idx])
        '''
        if self.controller.spike_index == []:
            return

        #waveforms
        if self.params['summary_statistics']=='median/mad':
            key1, key2 = 'median', 'mad'
            zero_centroids = False
        elif self.params['summary_statistics']=='mean/std':
            key1, key2 = 'mean', 'std'
            zero_centroids = False
        elif self.params['summary_statistics']=='none':
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
        
        common_channels = self.controller.channels
        self._common_channels_flat = common_channels

        if self.params['plot_limit_for_flatten'] and not self.is_span_added:
            self.addSpan(self.plot1, width, common_channels, n_left)
            self.addSpan(self.plot2, width, common_channels, n_left)
            self.is_span_added = True

        '''if self.params['display_threshold']:
            thresh = self.controller.get_threshold()
            thresh_line = pg.InfiniteLine(pos=thresh, angle=0, movable=False, pen = pg.mkPen('w'))
            self.plot1.addItem(thresh_line)'''
        
        xvect = None
        for idx, (k, v) in enumerate(cluster_visible.items()):
            if not (v and k>=0):
                continue
            color = self.controller.qcolors.get(k, QT.QColor('white'))
            color2 = QT.QColor(self.controller.qcolors[k])
            color2.setAlpha(self.alpha)
            wf0, chans = self.controller.get_waveform_centroid(k, key1, channels=common_channels)
            if wf0 is None: continue
            if ds_ratio > 1:
                wf0 = wf0[::ds_ratio, :]
            if xvect is None:
                xvect = np.arange(wf0.shape[0] * len(common_channels))
            wf0 = wf0.T.flatten()
            mad, chans = self.controller.get_waveform_centroid(k, key2, channels=common_channels)
            if mad is not None:
                if ds_ratio > 1:
                    mad = mad[::ds_ratio, :]
            self.curves_geometry[idx].setData(xvect, wf0)
            self.curves_geometry[idx].setPen(color, width=self.params['line_width'])
            if self.params['fillbetween'] and mad is not None:
                mad = mad.T.flatten()
                if zero_centroids:
                    self.curves_mad_top[idx].setData([], [])
                    self.curves_mad_bottom[idx].setData([], [])
                else:
                    self.curves_mad_top[idx].setData(xvect, wf0+mad)
                    self.curves_mad_top[idx].setPen(color2, width=self.params['line_width'])
                    self.curves_mad_top[idx].show()
                    self.curves_mad_bottom[idx].setData(xvect, wf0-mad)
                    self.curves_mad_bottom[idx].setPen(color2, width=self.params['line_width'])
                    self.curves_mad_bottom[idx].show()
                self.curves_mad_fill[idx].setCurves(
                    curve1=self.curves_mad_top[idx],
                    curve2=self.curves_mad_bottom[idx])
            if mad is not None:
                if zero_centroids:
                    self.curves_mad_plot2[idx].setData([], [])
                else:
                    self.curves_mad_plot2[idx].setData(xvect, mad)   
                    self.curves_mad_plot2[idx].setPen(color, width=self.params['line_width']) 
                    self.curves_mad_plot2[idx].show()
        #
        if self.params['show_channel_num']:
            for i, itemtext in enumerate(self.channel_num_labels):
                itemtext.setPos(width*i, 0)
                itemtext.setAngle(90)
                itemtext.show()
        else:
            for itemtext in self.channel_num_labels:
                itemtext.hide()
        if self._x_range is None or not keep_range :
            if xvect.size > 0:
                self._x_range = xvect[0], xvect[-1]
                self._y1_range = self.wf_min * 1.1, self.wf_max * 1.1
                self._y2_range = 0., 5.
        
        if self._x_range is not None:
            self.plot1.setXRange(*self._x_range, padding = 0.0)
            self.plot1.setYRange(*self._y1_range, padding = 0.0)
            self.plot2.setYRange(*self._y2_range, padding = 0.0)
        if LOGGING: logger.info(f'Finished _refresh_mode_flatten...')

    def refresh_mode_geometry(self, cluster_visible, keep_range):
        if LOGGING: logger.info(f'Starting _refresh_mode_geometry...')
        if self._x_range is not None and keep_range:
            #this may change with pyqtgraph
            self._x_range = tuple(self.viewBox1.state['viewRange'][0])
            self._y1_range = tuple(self.viewBox1.state['viewRange'][1])

        if self.xvect is None:
            return

        n_left, n_right = self.controller.get_waveform_left_right()
        if n_left is None:
            return
        width = n_right - n_left
        
        if width != self.xvect.shape[1]:
            self.initialize_plot()

        if self.params['summary_statistics']=='median/mad':
            key1, key2 = 'median', 'mad'
            zero_centroids = False
        elif self.params['summary_statistics']=='mean/std':
            key1, key2 = 'mean', 'std'
            zero_centroids = False
        elif self.params['summary_statistics']=='none':
            key1, key2 = 'mean', 'std'
            zero_centroids = True

        max_num_points = int(self.params['max_num_points'] / self.controller.nb_channel)
        ds_ratio = width // max_num_points + 1
        for idx, (k, v) in enumerate(cluster_visible.items()):
            if not (v and k>=0):
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
            color = self.controller.qcolors.get(k, QT.QColor('white'))
            if zero_centroids:
                self.curves_geometry[idx].setData([], [])
            else:
                # print(f'wf = {wf}')
                self.curves_geometry[idx].setData(xvect.flatten(), wf.T.flatten(), connect=connect.T.flatten())
                self.curves_geometry[idx].setPen(color, width=self.params['line_width'])
                self.curves_geometry[idx].show()
        if self.params['show_channel_num']:
            for i, itemtext in enumerate(self.channel_num_labels):
                x, y = self.arr_geometry[i, : ]
                itemtext.setPos(x, y)
                itemtext.show()
        else:
            for itemtext in self.channel_num_labels:
                itemtext.hide()
        #~ if self._x_range is None:
        if self._x_range is None or not keep_range:
            self._x_range = np.min(self.xvect), np.max(self.xvect)
            self._y1_range = np.min(self.arr_geometry[:,1])-self.delta_y*2, np.max(self.arr_geometry[:,1])+self.delta_y*2

        self.plot1.setXRange(*self._x_range, padding = 0.0)
        self.plot1.setYRange(*self._y1_range, padding = 0.0)
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
                color = self.controller.qcolors.get(k, QT.QColor('white'))
                if self.mode=='flatten':
                    if self._common_channels_flat is None:
                        curve.setData([], [])
                        return
                    wf = wf[:, self._common_channels_flat].T.flatten()
                    xvect = np.arange(wf.size)
                    curve.show()
                    curve.setData(xvect, wf)
                    curve.setPen(color, width=self.params['line_width'])
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
                    curve.show()
                    curve.setData(xvect.flatten(), wf.T.flatten(), connect=connect.T.flatten())
                    curve.setPen(color, width=self.params['line_width'])
        if n_spikes < max_n_spikes:
            for idx in range(n_spikes, max_n_spikes):
                curve = self.curves_individual[idx]
                curve.setData([], [])
        if LOGGING: logger.info('Finished _refresh_individual')

    def on_spike_selection_changed(self):
        #~ n_selected = np.sum(self.controller.spike_selection)
        #~ self._refresh_one_spike(n_selected)
        if LOGGING: logger.info('Starting on_spike_selection_changed')
        # self.refresh(keep_range=True)
        if LOGGING: logger.info('Finished on_spike_selection_changed')




class WaveformViewer(WaveformViewerBase):
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
        {'name': 'plot_selected_spike', 'type': 'bool', 'value': False },
        {'name': 'show_only_selected_cluster', 'type': 'bool', 'value': False},
        {'name': 'plot_limit_for_flatten', 'type': 'bool', 'value': True },
        {'name': 'summary_statistics', 'type': 'list', 'values': ['median/mad', 'mean/std', 'none'] },
        {'name': 'fillbetween', 'type': 'bool', 'value': True },
        {'name': 'show_channel_num', 'type': 'bool', 'value': False},
        # {'name': 'flip_bottom_up', 'type': 'bool', 'value': False},
        # {'name': 'display_threshold', 'type': 'bool', 'value' : True },
        # {'name': 'sparse_display', 'type': 'bool', 'value' : True },
        ]
        

class PeelerWaveformViewer(WaveformViewerBase):
    """
    **Waveform viewer** 
    """
    _params = [
        {'name': 'plot_selected_spike', 'type': 'bool', 'value': True },
        {'name': 'show_only_selected_cluster', 'type': 'bool', 'value': True},
        {'name': 'plot_limit_for_flatten', 'type': 'bool', 'value': True },
        {'name': 'summary_statistics', 'type': 'list', 'values': ['median/mad'] },
        {'name': 'fillbetween', 'type': 'bool', 'value': True },
        {'name': 'show_channel_num', 'type': 'bool', 'value': False},
        # {'name': 'flip_bottom_up', 'type': 'bool', 'value': False},
        # {'name': 'display_threshold', 'type': 'bool', 'value' : True },
        # {'name': 'sparse_display', 'type': 'bool', 'value' : True },
        ]


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
        {'name': 'max_num_points', 'type' :'int', 'value' : 4000, 'limits':[100, np.inf]},
        {'name': 'plot_individual_spikes', 'type': 'list', 'value': 'last', 'values': ['last', 'selected', 'none']},
        {'name': 'individual_spikes_num', 'type' :'int', 'value' : 5, 'limits':[1, np.inf]},
        {'name': 'show_only_selected_cluster', 'type': 'bool', 'value': False},
        {'name': 'plot_limit_for_flatten', 'type': 'bool', 'value': True},
        {'name': 'summary_statistics', 'type': 'list', 'value': 'none', 'values': ['median/mad', 'none'] },
        {'name': 'fillbetween', 'type': 'bool', 'value': True},
        {'name': 'show_channel_num', 'type': 'bool', 'value': True},
        # {'name': 'flip_bottom_up', 'type': 'bool', 'value': False},
        # {'name': 'display_threshold', 'type': 'bool', 'value' : False},
        # {'name': 'sparse_display', 'type': 'bool', 'value' : False },
        {'name': 'line_width', 'type': 'float', 'value': 1., 'limits': (0, np.inf)},
        ]
