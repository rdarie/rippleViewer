
import numpy as np
import sklearn.metrics

from pyqtgraph.util.mutex import Mutex

from ephyviewer.myqt import QT, QT_LIB

from pyacq.core import ThreadPollInput, RingBuffer
from pyacq.dsp.triggeraccumulator import TriggerAccumulator, ThreadPollInputUntilPosLimit
from pyacq.viewers.ephyviewer_mixin import RefreshTimer
from pyacq.devices.ripple import _dtype_stim_packet, _zero_stim_packet
from pyRippleViewer.tridesclous import labelcodes
from pyRippleViewer.tridesclous.base import ControllerBase
from pyRippleViewer.tridesclous.onlinepeaklists import OnlinePeakListSimple, OnlineClusterList
from pyRippleViewer.tridesclous.onlinewaveformviewer_vispy import RippleWaveformViewer
from pyRippleViewer.tridesclous.main_tools import (median_mad, mean_std, make_color_dict, get_color_palette)

import pdb, traceback

_dtype_peak = [
    ('index', 'int64'),
    ('cluster_label', 'int64'),
    ('channel', 'int64'),
    ('segment', 'int64'),
    ('extremum_amplitude', 'float64'),
    ('timestamp', 'float64'),
    ]

_dtype_peak_zero = np.zeros((1,), dtype=_dtype_peak)
_dtype_peak_zero['cluster_label'] = labelcodes.LABEL_UNCLASSIFIED

_dtype_cluster = [
    ('cluster_label', 'int64'),
    ('cell_label', 'int64'), 
    ('extremum_channel', 'int64'),
    ('extremum_amplitude', 'float64'),
    ('waveform_rms', 'float64'),
    ('nb_peak', 'int64'), 
    ('tag', 'U16'),
    ('annotations', 'U32'),
    ('color', 'uint32'),
    #
    ('elecCath', '8u1'),
    ('elecAno', '8u1'),
    ('amp', 'u4'),
    ('freq', 'u4'),
    ('pulseWidth', 'u4'),
    ('amp_steps', 'u4'),
    ('stim_res', 'u4')
    ]


class RippleTriggerAccumulator(TriggerAccumulator):
    """
    Here the list of theses attributes with shape and dtype. **N** is the total 
    number of peak detected. **M** is the number of selected peak for
    waveform/feature/cluser. **C** is the number of clusters
      * all_peaks (N, ) dtype = {0}
      * clusters (c, ) dtype= {1}
      * some_peaks_index (M) int64
      * centroids_median (C, width, nb_channel) float32
      * centroids_mad (C, width, nb_channel) float32
      * centroids_mean (C, width, nb_channel) float32
      * centroids_std (C, width, nb_channel) float32
    """.format(_dtype_peak, _dtype_cluster)
    
    _input_specs = {
        'signals' : dict(streamtype = 'signals'), 
        'events' : dict(streamtype = 'events',  shape = (-1,)),
        'stim_packets' : dict(streamtype = 'events',  shape = (-1,)),
        }
    _output_specs = {}
    
    _default_params = [
        {'name': 'left_sweep', 'type': 'float', 'value': -.1, 'step': 0.1,'suffix': 's', 'siPrefix': True},
        {'name': 'right_sweep', 'type': 'float', 'value': .2, 'step': 0.1, 'suffix': 's', 'siPrefix': True},
        {'name': 'stack_size', 'type' :'int', 'value' : 500,  'limits':[1, np.inf] },
        ]
    
    unique_stim_param_names = [
        'elecCath', 'elecAno', 'amp', 'freq', 'pulseWidth', 'amp_steps', 'stim_res']
    
    # _special_labels = [labelcodes.LABEL_UNCLASSIFIED, labelcodes.LABEL_TRASH]
    
    _special_labels = [labelcodes.LABEL_UNCLASSIFIED]
    
    new_spikes = QT.pyqtSignal()
    new_cluster = QT.pyqtSignal(int)
    
    def __init__(
            self, parent=None, **kargs,
            ):
        TriggerAccumulator.__init__(self, parent=parent, **kargs)
        # only capture triggers that are at least one sample apart
        # we initialize it to 1, to avoid double detecting instances of, e.g., stim on multiple channels
        # triggering once per channel
        self.debounce_timestamps = 1
    
    def _configure(
            self, max_stack_size=2000, max_xsize=2.,
            channel_group=None, debounce=None):
        """
        Arguments
        ---------------
        max_stack_size: int
            maximum size for the event size
        max_xsize: int 
            maximum sample chunk size
        events_dtype_field : None or str
            Standart dtype for 'events' input is 'int64',
            In case of complex dtype (ex : dtype = [('index', 'int64'), ('label', 'S12), ) ] you can precise which
            filed is the index.
        """
        if debounce is not None:
            # self.debounce_timestamps is in NIP samples (30 kHz)
            # debounce is in seconds
            self.debounce_timestamps = max(1, int(30e3 * debounce))
        #
        self.params.sigTreeStateChanged.connect(self.on_params_change)
        self.max_stack_size = max_stack_size
        self.events_dtype_field = 'timestamp'
        self.params.param('stack_size').setLimits([1, self.max_stack_size])
        self.max_xsize = max_xsize
        self.channel_group = channel_group
        self.channel_groups = {0: channel_group}

    def set_debounce(self, new_debounce):
        # self.debounce_timestamps is in NIP samples (30 kHz)
        # new_debounce is in seconds
        self.debounce_timestamps = max(1, int(30e3 * new_debounce))

    def after_input_connect(self, inputname):
        if inputname == 'signals':
            self.nb_channel = self.inputs['signals'].params['shape'][1]
            self.sample_rate = self.inputs['signals'].params['sample_rate']
            self.nip_sample_period = self.inputs['signals'].params['nip_sample_period']
        elif inputname == 'events':
            dt = np.dtype(self.inputs['events'].params['dtype'])
            assert self.events_dtype_field in dt.names, 'events_dtype_field not in input dtype {}'.format(dt)

    def _initialize(self):
        # set_buffer(self, size=None, double=True, axisorder=None, shmem=None, fill=None)
        bufferParams = {
            key: self.inputs['signals'].params[key]
            for key in ['double', 'axisorder', 'fill']}
        bufferParams['size'] = self.inputs['signals'].params['buffer_size']
        # print(f"self.inputs['signals'].params['buffer_size'] = {self.inputs['signals'].params['buffer_size']}")
        if (self.inputs['signals'].params['transfermode'] == 'sharedmem'):
            if 'shm_id' in self.inputs['signals'].params:
                bufferParams['shmem'] = self.inputs['signals'].params['shm_id']
            else:
                bufferParams['shmem'] = True
        else:
            bufferParams['shmem'] = None
        self.inputs['signals'].set_buffer(**bufferParams)
        #
        self.trig_poller = ThreadPollInput(
            self.inputs['events'], return_data=True)
        self.trig_poller.new_data.connect(self.on_new_trig)
        #
        self.stim_packet_poller = ThreadPollInput(
            self.inputs['stim_packets'], return_data=True)
        self.stim_packet_poller.new_data.connect(self.on_new_stim_packet)
        
        self.limit_poller = ThreadPollInputUntilPosLimit(self.inputs['signals'])
        self.limit_poller.limit_reached.connect(self.on_limit_reached)
        
        self.stack_lock = Mutex()
        self.wait_thread_list = []
        self.remake_stack()
        self.last_trigger_timestamp = -1
        self.last_unique_cluster_label = -1

        self.nb_segment = 1
        self.total_channel = self.nb_channel
        self.source_dtype = np.dtype('float64')

        clean_shape = lambda shape: tuple(int(e) for e in shape)
        self.segment_shapes = [
            clean_shape(self.get_segment_shape(s))
            for s in range(self.nb_segment)]

        channel_info = self.inputs['signals'].params['channel_info']
        self.all_channel_names = [
            item['name'] for item in channel_info
            ]
        self.datasource = DummyDataSource(self.all_channel_names)
        ####
        self.clusters = np.zeros(
            shape=(len(self._special_labels),), dtype=_dtype_cluster)
        self.clusters['cluster_label'] = self._special_labels
        self.current_stim_cluster = np.zeros(shape=(1,), dtype=_dtype_cluster)
        ####
        self._all_peaks_buffer = RingBuffer(
            shape=(self.params['stack_size'], 1), dtype=_dtype_peak,
            fill=_dtype_peak_zero)
        self.some_peaks_index = np.arange(self._all_peaks_buffer.shape[0])
        self.n_spike_for_centroid = 500
        #
        self.make_centroids()

    def make_centroids(self):
        n_left = self.limit1
        n_right = self.limit2
        #
        self.centroids_median = np.zeros((self.cluster_labels.size, n_right - n_left, self.nb_channel), dtype=self.source_dtype)
        self.centroids_mad = np.ones((self.cluster_labels.size, n_right - n_left, self.nb_channel), dtype=self.source_dtype)
        self.centroids_mean = np.zeros((self.cluster_labels.size, n_right - n_left, self.nb_channel), dtype=self.source_dtype)
        self.centroids_std = np.ones((self.cluster_labels.size, n_right - n_left, self.nb_channel), dtype=self.source_dtype)

    def _start(self):
        self.trig_poller.start()
        self.stim_packet_poller.start()
        self.limit_poller.start()

    def _stop(self):
        self.trig_poller.stop()
        self.trig_poller.wait()
        self.stim_packet_poller.stop()
        self.stim_packet_poller.wait()
        self.limit_poller.stop()
        self.limit_poller.wait()
        
        for thread in self.wait_thread_list:
            thread.stop()
            thread.wait()
        self.wait_thread_list = []

    def on_new_stim_packet(
            self, packet_index, stim_packet):
        # print(f'RippleTriggerAccumulator, on_new_stim_packet: {stim_packet}')
        alreadySeen = stim_packet[self.unique_stim_param_names] in self.clusters[self.unique_stim_param_names]
        if not alreadySeen:
            newCluster = np.zeros((1,), dtype=_dtype_cluster)
            self.last_unique_cluster_label += 1
            newCluster['cluster_label'] = self.last_unique_cluster_label
            newCluster[self.unique_stim_param_names] = stim_packet[self.unique_stim_param_names]
            self.current_stim_cluster = newCluster
            self.clusters = np.concatenate([self.clusters, newCluster])
            ##
            n_left = self.limit1
            n_right = self.limit2
            ## add blank entry to summary stats
            for attrName in ['centroids_mad', 'centroids_std']:
                expandedArr = np.concatenate(
                    [getattr(self, attrName),
                    np.ones((1, n_right - n_left, self.nb_channel),
                    dtype=self.source_dtype)])
                setattr(self, attrName, expandedArr)
            for attrName in ['centroids_median', 'centroids_mean']:
                expandedArr = np.concatenate(
                    [getattr(self, attrName),
                    np.zeros((1, n_right - n_left, self.nb_channel), dtype=self.source_dtype)])
                setattr(self, attrName, expandedArr)
            ##
            self.refresh_colors()
            self.new_cluster.emit(self.last_unique_cluster_label)
        else:
            mask = (self.clusters[self.unique_stim_param_names] == stim_packet[self.unique_stim_param_names])
            assert mask.sum() == 1
            self.current_stim_cluster = self.clusters[mask]
        return

    def on_new_trig(
            self, trig_num, trig_indexes, verbose=False):
        # if LOGGING:
        #     logger.info(f'on_new_trig: {trig_indexes}')
        # add to all_peaks
        #################################################################
        ## debounce the triggers as they come in
        # self.debounce_timestamps is in NIP samples (30 kHz)
        trig_timestamps = trig_indexes[self.events_dtype_field].flatten()
        # sort the triggers to find the inter-trigger interval
        sorted_indexes = np.argsort(trig_timestamps)
        trig_indexes = trig_indexes[sorted_indexes]
        trig_timestamps = trig_timestamps[sorted_indexes]
        ##
        if verbose:
            debounce = self.debounce_timestamps / 3e4
            print(f"\non_new_trig, self.debounce_timestamps = {self.debounce_timestamps} ({debounce:.3f} sec)")
            trig_times = trig_timestamps / 3e4
            print(f"on_new_trig, before debounce: trig_times = {trig_times} (sec)")
        ###
        if self.last_trigger_timestamp == -1:
            # add a dummy value to make sure we accept the first trigger
            inter_trig_intervals = np.concatenate([[self.debounce_timestamps], np.diff(trig_timestamps)])
        else:
            inter_trig_intervals = np.diff(np.concatenate([[self.last_trigger_timestamp], trig_timestamps]))
            if inter_trig_intervals[0] >= self.debounce_timestamps:
                # we are going to trigger on the first timestamp
                inter_trig_intervals[0] = self.debounce_timestamps
        # count the number of times we rolled over past the debounce threshold
        div_result = np.cumsum(inter_trig_intervals) // self.debounce_timestamps
        ##
        if verbose:
            print(f"on_new_trig, inter_trig_intervals = {inter_trig_intervals}")
            print(f"on_new_trig, div_result = {div_result}")
        ##
        _, unique_indices = np.unique(div_result, return_index=True)
        unique_nonzero_indices = [uidx for uidx in unique_indices if div_result[uidx] > 0]
        ##
        if verbose:
            print(f"on_new_trig, unique_indices = {unique_indices}")
            print(f"on_new_trig, unique_nonzero_indices = {unique_nonzero_indices}")
        if not len(unique_nonzero_indices):
            if verbose:
                print(f"on_new_trig, no indices left, returning..")
            return
        ##
        #
        trig_indexes = trig_indexes[unique_nonzero_indices]
        trig_timestamps = trig_timestamps[unique_nonzero_indices]
        #
        self.last_trigger_timestamp = trig_timestamps[-1]
        ##
        if verbose:
            trig_times = trig_timestamps / 3e4
            print(f"on_new_trig, after debounce: trig_times = {trig_times} (sec)\n")
        ##
        adj_index = (
            trig_timestamps / self.nip_sample_period).astype('int64')
        for trig_index in adj_index:
            self.limit_poller.append_limit(trig_index + self.limit2)
        data = np.zeros(trig_indexes.shape, dtype=_dtype_peak)
        data['timestamp'] = trig_timestamps
        data['index'] = adj_index
        data['cluster_label'] = self.current_stim_cluster['cluster_label']
        data['channel'] = 0
        data['segment'] = 0
        self.clusters['nb_peak'][self.clusters['cluster_label'] == self.current_stim_cluster['cluster_label']] += data.shape[0]
        self._all_peaks_buffer.new_chunk(data[:, None])
        self.new_spikes.emit()
        return

    def on_limit_reached(self, limit_index):
        # if LOGGING:
        #     logger.info(f'on limit reached: {limit_index-self.size}:{limit_index}')
        arr = self.get_signals_chunk(i_start=limit_index-self.size, i_stop=limit_index)
        if arr is not None:
            self.stack.new_chunk(arr.reshape(1, (self.limit2 - self.limit1) * self.nb_channel))

    def remake_stack(self):
        self.limit1 = l1 = int(self.params['left_sweep'] * self.sample_rate)
        self.limit2 = l2 = int(self.params['right_sweep'] * self.sample_rate)
        self.size = l2 - l1
        
        self.t_vect = np.arange(l2 - l1) / self.sample_rate + self.params['left_sweep']
        self.stack = RingBuffer(
            shape=(self.params['stack_size'], (l2-l1) * self.nb_channel),
            dtype='float64')
        self.limit_poller.reset()

    def get_geometry(self):
        """
        Get the geometry for a given channel group in a numpy array way.
        """
        geometry = [ self.channel_group['geometry'][chan] for chan in self.channel_group['channels'] ]
        geometry = np.array(geometry, dtype='float64')
        return geometry
    
    def get_channel_distances(self):
        geometry = self.get_geometry()
        distances = sklearn.metrics.pairwise.euclidean_distances(geometry)
        return distances
    
    def get_channel_adjacency(self, adjacency_radius_um=None):
        assert adjacency_radius_um is not None
        channel_distances = self.get_channel_distances()
        channels_adjacency = {}
        for c in range(self.nb_channel):
            nearest, = np.nonzero(channel_distances[c, :] < adjacency_radius_um)
            channels_adjacency[c] = nearest
        return channels_adjacency

    def get_segment_length(self, seg_num):
        """
        Segment length (in sample) for a given segment index
        """
        return self.inputs['signals'].buffer.index()
    
    def get_segment_shape(self, seg_num):
        return self.inputs['signals'].buffer.shape

    def get_signals_chunk(
        self, seg_num=0, chan_grp=0,
        signal_type='initial',
        i_start=None, i_stop=None, pad_width=0):
        """
        Get a chunk of signal for for a given segment index and channel group.
        
        Parameters
        ------------------
        seg_num: int
            segment index
        chan_grp: int
            channel group key
        i_start: int or None
           start index (included)
        i_stop: int or None
            stop index (not included)
        pad_width: int (0 default)
            Add optional pad on each sides
            usefull for filtering border effect
        
        """
        channels = self.channel_group['channels']
        #
        sig_chunk_size = i_stop - i_start
        first = self.inputs['signals'].buffer.first_index()
        last = self.inputs['signals'].buffer.index()
        #
        after_padding = False
        if i_start >= last or i_stop <= first:
            return np.zeros((sig_chunk_size, len(channels)), dtype='float64')
        if i_start < first:
            pad_left = first - i_start
            i_start = first
            after_padding = True
        else:
            pad_left = 0
        if i_stop > last:
            pad_right = i_stop - last
            i_stop = last
            after_padding = True
        else:
            pad_right = 0
        #
        data = self.inputs['signals'].get_data(i_start, i_stop, copy=False, join=True)
        data = data['value']
        data = data[:, channels]
        #
        if after_padding:
            # finalize padding on border
            data2 = np.zeros((data.shape[0] + pad_left + pad_right, data.shape[1]), dtype=data.dtype)
            data2[pad_left:data2.shape[0]-pad_right, :] = data
            return data2
        return data

    def get_some_waveforms(
        self, seg_num=None, chan_grp=0,
        peak_sample_indexes=None, peaks_index=None,
        n_left=None, n_right=None, waveforms=None, channel_indexes=None):
        """
        Exctract some waveforms given sample_indexes
        seg_num is int then all spikes come from same segment
        if seg_num is None then seg_nums is an array that contain seg_num for each spike.
        """
        if channel_indexes is None:
            channel_indexes = slice(None)
        #
        if peaks_index is None:
            # print(f'get_some_waveforms( peak_sample_indexes = {peak_sample_indexes}')
            assert peak_sample_indexes is not None, 'Provide sample_indexes'
            peaks_index = np.flatnonzero(np.isin(self.all_peaks['index'], peak_sample_indexes))
        # peaks_index = self.params['stack_size'] - peaks_index - 1
        # print(f'get_some_waveforms( peaks_index = {peaks_index}')
        '''
        with self.stack_lock:
            waveforms = self.stack[:, :, channel_indexes]
            waveforms = waveforms[peaks_index, :, :]
            '''
        first = self.stack.first_index()
        if isinstance(peaks_index, (int, np.int64)):
            waveforms_flat = self.stack.get_data(start=peaks_index+first, stop=peaks_index+first+1).copy()
            waveforms = waveforms_flat.reshape(self.limit2-self.limit1, self.nb_channel)
        elif isinstance(peaks_index, slice):
            waveforms_flat = self.stack[peaks_index]
            waveforms = np.zeros((waveforms_flat.shape[0], self.limit2-self.limit1, self.nb_channel), dtype='float64')
            for pk_index in range(waveforms_flat.shape[0]):
                waveforms[pk_index, :, :] = waveforms_flat[pk_index, :].reshape(self.limit2-self.limit1, self.nb_channel)
        else:
            waveforms = np.zeros((len(peaks_index), self.limit2-self.limit1, self.nb_channel), dtype='float64')
            for idx, pk_index in enumerate(peaks_index):
                waveforms_flat = self.stack.get_data(start=pk_index + first, stop=pk_index + first + 1, copy=True, join=True)
                waveforms[idx, :, :] = waveforms_flat.reshape(self.limit2-self.limit1, self.nb_channel)
        # print(f'get_some_waveforms( {waveforms[0, :, :]}')
        return waveforms
    
    @property
    def all_peaks(self):
        start = self._all_peaks_buffer.first_index()
        stop = self._all_peaks_buffer.index()
        return self._all_peaks_buffer.get_data(start, stop, copy=False, join=True)

    ## catalogue constructor properties
    @property
    def nb_peak(self):
        return self._all_peaks_buffer.shape[0]

    @property
    def cluster_labels(self):
        if self.clusters is not None:
            return self.clusters['cluster_label']
        else:
            return np.array([], dtype='int64')
    
    @property
    def positive_cluster_labels(self):
        return self.cluster_labels[self.cluster_labels >= 0] 

    def index_of_label(self, label):
        ind = np.nonzero(self.clusters['cluster_label'] == label)[0][0]
        return ind

    def recalc_cluster_info(self, removeEmpty=False):
        for k in self.cluster_labels:
            self.clusters['nb_peak'][self.clusters['cluster_label'] == k] = (self.all_peaks['cluster_label'] == k).sum()
        if removeEmpty:
            mask = (self.clusters['cluster_label'] < 0) | (self.clusters['nb_peak'] <= 0)
            self.clusters = self.clusters[mask]
        pass

    def compute_one_centroid(
            self, k, flush=True,
            n_spike_for_centroid=None):
        
        if n_spike_for_centroid is None:
            n_spike_for_centroid = self.n_spike_for_centroid
        
        ind = self.index_of_label(k)
        
        n_left = self.limit1
        n_right = self.limit2
        
        # selected = np.flatnonzero(all_peaks['cluster_label'][self.some_peaks_index]==k).tolist()
        selected = np.flatnonzero(self.all_peaks['cluster_label'] == k)
        if selected.size == 0:
            return
        if selected.size > n_spike_for_centroid:
            keep = np.random.choice(
                selected.size, n_spike_for_centroid, replace=False)
            selected = selected[keep]
        
        wf = self.get_some_waveforms(
            seg_num=0,
            peaks_index=selected,
            n_left=n_left, n_right=n_right,
            waveforms = None, channel_indexes = None)
        
        med = np.nanmedian(wf, axis=0)
        med[np.isnan(med)] = 0.
        mad = np.nanmedian(np.abs(wf - med),axis=0) * 1.4826
        try:
            mad[(mad == 0) | np.isnan(mad)] = 1.
        except:
            traceback.print_exc()
            pdb.set_trace()
        
        '''
        print(
            f'k = {k}; ind = {ind}'
            f'median.shape = {med.shape}'
            f'mad = {mad.shape}'
            )'''

        # median, mad = mean_std(wf, axis=0)
        # to persistent arrays
        self.centroids_median[ind, :, :] = med
        self.centroids_mad[ind, :, :] = mad
        #~ self.centroids_mean[ind, :, :] = mean
        #~ self.centroids_std[ind, :, :] = std
        #
        self.centroids_mean[ind, :, :] = 0.
        self.centroids_std[ind, :, :] = 1.
        
    def compute_several_centroids(self, labels, n_spike_for_centroid=None):
        # TODO make this in paralell
        for k in labels:
            self.compute_one_centroid(k, flush=False, n_spike_for_centroid=n_spike_for_centroid)
        
    def compute_all_centroid(self, n_spike_for_centroid=None):
        self.make_centroids()
        self.compute_several_centroids(self.positive_cluster_labels, n_spike_for_centroid=n_spike_for_centroid)

    def _close(self):
        pass

    def refresh_colors(
            self, reset=True, palette='Set3', interleaved=False):
        
        labels = self.positive_cluster_labels
        
        if reset:
            n = labels.size
            if interleaved and n>1:
                n1 = np.floor(np.sqrt(n))
                n2 = np.ceil(n/n1)
                n = int(n1*n2)
                n1, n2 = int(n1), int(n2)
        else:
            n = np.sum((self.clusters['cluster_label'] >= 0) & (self.clusters['color'] == 0))

        if n>0:
            colors_int32 = get_color_palette(n, palette=palette, output='int32')
            
            if reset and interleaved and n > 1:
                colors_int32 = colors_int32.reshape(n1, n2).T.flatten()
                colors_int32 = colors_int32[:labels.size]
            
            if reset:
                mask = self.clusters['cluster_label'] >= 0
                self.clusters['color'][mask] = colors_int32
            else:
                mask = (self.clusters['cluster_label'] >= 0) & (self.clusters['color'] == 0)
                self.clusters['color'][mask] = colors_int32
        
        #Make colors accessible by key
        self.colors = make_color_dict(self.clusters)


class RippleCatalogueController(ControllerBase):
    
    def __init__(self, dataio=None, chan_grp=None, parent=None):
        ControllerBase.__init__(self, parent=parent)
        
        self.dataio = dataio

        self.dataio.trig_poller.new_data.connect(self.update_visible_spikes)

        if chan_grp is None:
            chan_grp = 0
        self.chan_grp = chan_grp

        self.geometry = self.dataio.get_geometry()

        self.nb_channel = self.dataio.nb_channel
        self.channels = np.arange(self.nb_channel, dtype='int64')

        self.init_plot_attributes()

        self.dataio.new_cluster.connect(self.check_plot_attributes)

    def init_plot_attributes(self):
        self.new_clusters_visible = True
        self.cluster_visible = {k: k >= 0 for k in self.cluster_labels}
        self.spike_selection = np.zeros(self.dataio.nb_peak, dtype='bool')
        self.spike_visible = self.dataio.all_peaks['cluster_label'].flatten() >= 0
        self.check_plot_attributes()
    
    def check_plot_attributes(self):
        # align cluster visibility dict with cluster labels
        for k in self.cluster_labels:
            if k not in self.cluster_visible:
                # k is a cluster label we've never seen before
                self.cluster_visible[k] = (k >= 0) and self.new_clusters_visible
        for k in self.cluster_visible:
            if k not in self.cluster_labels and (k >= 0):
                # k used to exist, but now it doesn't
                self.cluster_visible.pop(k)
        for code in self.dataio._special_labels:
            if code not in self.cluster_visible:
                self.cluster_visible[code] = False
        self.refresh_colors(reset=False)
        self.do_cluster_count()
    
    def do_cluster_count(self):
        self.cluster_count = {c['cluster_label']: c['nb_peak'] for c in self.clusters}
        for code in self.dataio._special_labels:
            self.cluster_count[code] = 0

    def reload_data(self):
        self.dataio.compute_all_centroid()
        self.dataio.recalc_cluster_info(removeEmpty=False)
        self.init_plot_attributes()

    @property
    def spikes(self):
        return self.dataio.all_peaks.flatten()
    
    @property
    def all_peaks(self):
        return self.dataio.all_peaks.flatten()
    
    @property
    def clusters(self):
        return self.dataio.clusters
    
    @property
    def cluster_labels(self):
        return self.dataio.clusters['cluster_label']
    
    @property
    def positive_cluster_labels(self):
        return self.cluster_labels[self.cluster_labels >= 0]
    
    @property
    def cell_labels(self):
        return self.dataio.clusters['cell_label']
        
    @property
    def spike_index(self):
        # return self.dataio.all_peaks[:]['index']
        return self.all_peaks['index']

    @property
    def some_peaks_index(self):
        return self.dataio.some_peaks_index

    @property
    def spike_label(self):
        return self.all_peaks['cluster_label'].flatten()
    
    @property
    def spike_channel(self):
        return self.all_peaks['channel']

    @property
    def spike_segment(self):
        return self.all_peaks['segment']
    
    @property
    def have_sparse_template(self):
        return False

    def get_waveform_left_right(self):
        return self.dataio.limit1, self.dataio.limit2
    
    def get_some_waveforms(
            self, seg_num, peak_sample_indexes, channel_indexes,
            peaks_index=None):
        n_left, n_right = self.get_waveform_left_right()

        waveforms = self.dataio.get_some_waveforms(
            seg_num=seg_num, chan_grp=self.chan_grp,
            peak_sample_indexes=peak_sample_indexes,
            peaks_index=peaks_index,
            n_left=n_left, n_right=n_right, channel_indexes=channel_indexes)
        return waveforms

    @property
    def info(self):
        return self.dataio.info

    def get_extremum_channel(self, label):
        if label<0:
            return None
        
        ind, = np.nonzero(self.dataio.clusters['cluster_label']==label)
        if ind.size!=1:
            return None
        ind = ind[0]
        
        extremum_channel = self.dataio.clusters['extremum_channel'][ind]
        if extremum_channel >= 0:
            return extremum_channel
        else:
            return None
        
    def refresh_colors(self, reset=True, palette='Set3'):
        self.dataio.refresh_colors(reset=reset, palette=palette)
        
        self.qcolors = {}
        for k, color in self.dataio.colors.items():
            r, g, b = color
            self.qcolors[k] = QT.QColor(r*255, g*255, b*255)

    def update_visible_spikes(self):
        visibles = np.array([k for k, v in self.cluster_visible.items() if v])
        self.spike_visible[:] = np.in1d(self.spike_label, visibles)

    def on_cluster_visibility_changed(self):
        self.update_visible_spikes()
        ControllerBase.on_cluster_visibility_changed(self)

    def get_waveform_centroid(self, label, metric, sparse=False, channels=None):
        if label in self.dataio.clusters['cluster_label'] and self.dataio.centroids_median is not None:
            ind = self.dataio.index_of_label(label)
            attr = getattr(self.dataio, 'centroids_'+metric)
            wf = attr[ind, :, :]
            if channels is not None:
                chans = channels
                wf = wf[:, chans]
            else:
                chans = self.channels
            
            return wf, chans
        else:
            return None, None

    def get_min_max_centroids(self):
        if self.dataio.centroids_median is not None and self.dataio.centroids_median.size > 0:
            wf_min = self.dataio.centroids_median.min()
            wf_max = self.dataio.centroids_median.max()
        else:
            wf_min = 0.
            wf_max = 0.
        return wf_min, wf_max

    def get_min_max_dispersions(self):
        if self.dataio.centroids_mad is not None and self.dataio.centroids_mad.size > 0:
            mad_min = self.dataio.centroids_mad.min()
            mad_max = self.dataio.centroids_mad.max()
        else:
            mad_min = 0.
            mad_max = 0.
        return mad_min, mad_max
    
    @property
    def cluster_similarity(self):
        return None
   
    @property
    def cluster_ratio_similarity(self):
        return None

    def get_threshold(self):
        return 1.

    
class RippleTriggeredWindow(QT.QMainWindow):

    def __init__(
            self, dataio=None, refreshRateHz=2.,
            window_title="Triggered signal viewer"):

        QT.QMainWindow.__init__(self)

        self.window_title = window_title
        self.setWindowTitle(self.window_title)

        self.refreshRateHz = refreshRateHz # Hz

        self.dataio = dataio
        
        self.controller = RippleCatalogueController(dataio=dataio)

        self.waveformviewer = RippleWaveformViewer(controller=self.controller, refreshRateHz=refreshRateHz)
        self.clusterlist = OnlineClusterList(controller=self.controller, refreshRateHz=refreshRateHz)
        self.peaklist = OnlinePeakListSimple(controller=self.controller, refreshRateHz=refreshRateHz)

        docks = {}

        docks['waveformviewer'] = QT.QDockWidget('waveformviewer', self)
        docks['waveformviewer'].setWidget(self.waveformviewer)
        self.addDockWidget(QT.Qt.RightDockWidgetArea, docks['waveformviewer'])

        docks['clusterlist'] = QT.QDockWidget('stim pattern list', self)
        docks['clusterlist'].setWidget(self.clusterlist)

        docks['peaklist'] = QT.QDockWidget('spike list', self)
        docks['peaklist'].setWidget(self.peaklist)
        self.addDockWidget(QT.Qt.LeftDockWidgetArea, docks['peaklist'])
        self.splitDockWidget(docks['peaklist'], docks['clusterlist'], QT.Qt.Vertical)

        self.create_actions()
        self.create_toolbar()
        '''
        # adjust dock sizes
        for dockName in ['waveformviewer']:
            thisQSize = docks[dockName].sizeHint()
            thisQSizePolicy = docks[dockName].sizePolicy()
            thisQSizePolicy.setHorizontalPolicy(QT.QSizePolicy.MinimumExpanding)
            thisQSizePolicy.setVerticalPolicy(QT.QSizePolicy.MinimumExpanding)
            thisQSizePolicy.setHorizontalStretch(10)
            docks[dockName].setSizePolicy(thisQSizePolicy)
            docks[dockName].setMinimumSize(thisQSize.width(), thisQSize.height())
        #
        for dockName in ['peaklist', 'clusterlist']:
            thisQSize = docks[dockName].sizeHint()
            thisQSizePolicy = docks[dockName].sizePolicy()
            thisQSizePolicy.setHorizontalPolicy(QT.QSizePolicy.Preferred)
            thisQSizePolicy.setVerticalPolicy(QT.QSizePolicy.Preferred)
            thisQSizePolicy.setHorizontalStretch(1)
            docks[dockName].setSizePolicy(thisQSizePolicy)
            docks[dockName].setMinimumSize(thisQSize.width(), thisQSize.height())'''

        '''thisQSize = self.sizeHint()
        self.resize(int(1.4 * thisQSize.width()), int(1.4 * thisQSize.height()))'''

        for view in self.controller.views:
            self.dataio.new_spikes.connect(view.refresh)
            view.connectedToIO = True
            view.enableRefresh()

        self.dataio.new_cluster.connect(self.waveformviewer.add_blank_curve)
        
    def create_actions(self):
        #~ self.act_refresh = QT.QAction('Refresh', self,checkable = False, icon=QT.QIcon.fromTheme("view-refresh"))
        self.act_refresh = QT.QAction(
            'recalc\nsummary\nstatistics', self, checkable=False, icon=QT.QIcon(":/view-refresh.svg"))
        self.act_refresh.triggered.connect(self.refresh_with_reload)
        
    def create_toolbar(self):
        self.toolbar = QT.QToolBar('Tools')
        self.toolbar.setToolButtonStyle(QT.Qt.ToolButtonTextUnderIcon)
        self.addToolBar(QT.Qt.RightToolBarArea, self.toolbar)
        self.toolbar.setIconSize(QT.QSize(60, 40))
        
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.act_refresh)

    def warn(self, title, text):
        mb = QT.QMessageBox.warning(self, title,text, QT.QMessageBox.Ok,  QT.QMessageBox.NoButton)
    
    def refresh_with_reload(self):
        self.controller.reload_data()
        #
        self.waveformviewer.recalc_y_range()
        self.waveformviewer.reset_y_factor()
        self.waveformviewer.clear_plots()
        return
    
    def closeEvent(self, event):
        # self.timer.stop()
        # 
        # self.thread.quit()
        # self.thread.wait()
        # 
        self.controller.dataio.stop()
        self.controller.dataio.close()
        event.accept()


class DummyDataSource:

    def __init__(self, channel_names):
        self.channel_names = channel_names

    def get_channel_names(self):
        return self.channel_names
