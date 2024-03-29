from ephyviewer.myqt import QT, QT_LIB
import pyqtgraph as pg

import time


class ControllerBase(QT.QObject):
    spike_selection_changed = QT.pyqtSignal()
    spike_label_changed = QT.pyqtSignal()
    colors_changed = QT.pyqtSignal()
    cluster_visibility_changed = QT.pyqtSignal()
    cluster_tag_changed = QT.pyqtSignal()
    
    def __init__(self, parent=None):
        QT.QObject.__init__(self, parent=parent)
        self.views = []
    
    def declare_a_view(self, new_view):
        assert new_view not in self.views, 'view already declared {}'.format(self)
        self.views.append(new_view)
        
        new_view.spike_selection_changed.connect(self.on_spike_selection_changed)
        new_view.spike_label_changed.connect(self.on_spike_label_changed)
        new_view.colors_changed.connect(self.on_colors_changed)
        new_view.cluster_visibility_changed.connect(self.on_cluster_visibility_changed)
        new_view.cluster_tag_changed.connect(self.on_cluster_tag_changed)
        
    def on_spike_selection_changed(self):
        for view in self.views:
            if view == self.sender(): continue
            view.on_spike_selection_changed()

    def on_spike_label_changed(self):
        for view in self.views:
            if view==self.sender(): continue
            #~ t1 = time.perf_counter()
            view.on_spike_label_changed()
            #~ t2 = time.perf_counter()
            #~ print('on_spike_label_changed',view,  t2-t1)
    
    def on_colors_changed(self):
        for view in self.views:
            if view==self.sender(): continue
            view.on_colors_changed()
    
    def on_cluster_visibility_changed(self):
        for view in self.views:
            if view==self.sender(): continue
            view.on_cluster_visibility_changed()

    def on_cluster_tag_changed(self):
        for view in self.views:
            if view==self.sender(): continue
            view.on_cluster_tag_changed()

    @property
    def channel_indexes(self):
        channel_group = self.dataio.channel_group
        return channel_group['channels']

    @property
    def channel_names(self):
        all_names = self.dataio.datasource.get_channel_names()
        return [all_names[c] for c in self.channel_indexes]
    
    @property
    def channel_indexes_and_names(self):
        all_names = self.dataio.datasource.get_channel_names()
        return [(c, all_names[c]) for c in self.channel_indexes]


class WidgetBase(QT.QWidget):

    spike_selection_changed = QT.pyqtSignal()
    spike_label_changed = QT.pyqtSignal()
    colors_changed = QT.pyqtSignal()
    cluster_visibility_changed = QT.pyqtSignal()
    cluster_tag_changed = QT.pyqtSignal()
    
    _params = None

    labels_in_table = []
    
    def __init__(
            self, parent = None, controller=None, refreshRateHz=1.):
        QT.QWidget.__init__(self, parent)
        self.controller = controller
        #
        self.sample_rate = self.controller.dataio.sample_rate
        self.refreshRateHz = refreshRateHz # Hz
        self.tNextRefresh = None
        self.connectedToIO = False

        if self.controller is not None:
            self.controller.declare_a_view(self)
        
        if self._params is not None:
            self.create_settings()
    
    def refresh(self, force=False):
        drawNow = False
        
        if self.tNextRefresh is None:
            if not force:
                return
            else:
                drawNow = True
        else:
            tNow = time.time()
            drawNow = (tNow >= self.tNextRefresh) or force

        if drawNow:
            self._refresh()
            self.tNextRefresh = time.time() + (self.refreshRateHz ** (-1))
        return

    def enableRefresh(self):
        self.tNextRefresh = time.time()

    def _refresh(self):
        raise(NotImplementedError)

    def create_settings(self):
        self.params = pg.parametertree.Parameter.create(
            name='settings', type='group', children=self._params)
        
        self.tree_params = pg.parametertree.ParameterTree(parent=self)
        self.tree_params.header().hide()
        self.tree_params.setParameters(self.params, showTop=True)
        self.tree_params.setWindowTitle(u'Settings')
        self.tree_params.setWindowFlags(QT.Qt.Window)
        
        self.params.sigTreeStateChanged.connect(self.on_params_changed)

    def open_settings(self):
        if not self.tree_params.isVisible():
            self.tree_params.show()
        else:
            self.tree_params.hide()
    
    def on_params_changed(self):
        # self.refresh()
        pass
    
    def on_spike_selection_changed(self):
        # self.refresh()
        pass

    def on_spike_label_changed(self):
        # self.refresh()
        pass
        
    def on_colors_changed(self):
        # self.refresh()
        pass
    
    def on_cluster_visibility_changed(self):
        # self.refresh()
        pass
    
    def on_cluster_tag_changed(self):
        pass
