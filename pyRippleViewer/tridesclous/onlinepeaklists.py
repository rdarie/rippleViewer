from ephyviewer.myqt import QT, QT_LIB

import numpy as np

from pyRippleViewer.tridesclous import labelcodes
from pyRippleViewer.tridesclous.base import WidgetBase

from pyRippleViewer.tridesclous.gui_tools import ParamDialog, open_dialog_methods
from pyRippleViewer.tridesclous import gui_params

from pyacq.devices.ripple import binaryToElecList
import pdb

checkboxLookup = {
    False: QT.Qt.Unchecked,
    True: QT.Qt.Checked}

pretty_names = {
    'cluster_label': 'stim. pattern ID',
    'elecCath': 'cathode(s)',
    'elecAno': 'anode(s)',
    'pulseWidth': 'pulse width (usec)',
    'amp': 'stim. amplitude (uA)',
    'freq': 'stim. frequency (Hz)',
    'time': 'time (sec)'
    }

class OnlinePeakModel(QT.QAbstractItemModel):
    labels_in_table = ['time', 'cluster_label']

    def __init__(self, parent = None, controller=None):
        QT.QAbstractItemModel.__init__(self,parent)
        self.controller = controller
        self.sample_rate = self.controller.dataio.sample_rate
        self.refresh_colors()
    
    def columnCount(self, parentIndex):
        return 2
        
    def rowCount(self, parentIndex):
        if not parentIndex.isValid() and self.controller.spike_label is not None:
            self.visible_ind, = np.nonzero(self.controller.spike_visible)
            n = self.visible_ind.size
            return n
        else :
            return 0
        
    def index(self, row, column, parentIndex):
        if not parentIndex.isValid():
            if column==0:
                childItem = row
            return self.createIndex(row, column, None)
        else:
            return QT.QModelIndex()
    
    def parent(self, index):
        return QT.QModelIndex()
    
    def data(self, index, role):
        if not index.isValid():
            return None
        
        if role not in (QT.Qt.DisplayRole, QT.Qt.DecorationRole):
            return
        
        col = index.column()
        row = index.row()
        #~ ind = self.visible_peak_labels.index[row]
        #~ label =  self.visible_peak_labels.iloc[row]
        #~ t_start = 0.
        
        abs_ind = self.visible_ind[row]
        # seg_num = self.controller.spike_segment[abs_ind]
        peak_pos = self.controller.spike_index[abs_ind]
        peak_time = peak_pos / self.sample_rate
        peak_label = self.controller.spike_label[abs_ind]
        peak_chan = self.controller.spike_channel[abs_ind]
        peak_ampl = self.controller.spikes[abs_ind]['extremum_amplitude']
        
        
        if role == QT.Qt.DisplayRole:
            if col == 0:
                return '{:.4f}'.format(peak_time)
            elif col == 1:
                return '{}'.format(peak_label)
            # elif col == 2:
            #     return '{}'.format(peak_chan)
            # elif col == 3:
            #     return '{:.1f}'.format(peak_ampl)
            # elif col == 4:
            #     return '{}'.format(peak_pos)
            else:
                return None
    
        elif role == QT.Qt.DecorationRole:
            if col != 0: return None
            if peak_label in self.icons:
                return self.icons[peak_label]
            else:
                return None
        else :
            return None
    
    def flags(self, index):
        if not index.isValid():
            return QT.Qt.NoItemFlags
        return QT.Qt.ItemIsEnabled | QT.Qt.ItemIsSelectable #| Qt.ItemIsDragEnabled

    def headerData(self, section, orientation, role):
        if orientation == QT.Qt.Horizontal and role == QT.Qt.DisplayRole:
            # return self.labels_in_table[section]
            return pretty_names.get(self.labels_in_table[section], self.labels_in_table[section])
        return
    
    def refresh_colors(self):
        self.icons = { }
        for k in self.controller.qcolors:
            color = self.controller.qcolors.get(k, QT.QColor( 'white'))
            pix = QT.QPixmap(10, 10)
            pix.fill(color)
            self.icons[k] = QT.QIcon(pix)
        
        #~ self.icons[-1] = QIcon(':/user-trash.png')
        
        self.layoutChanged.emit()


class OnlinePeakList(WidgetBase):
    """
    **Peak List** show all detected peak for the catalogue construction.
    
    Here pintentionally peaks are not spikes already (even most of them are spikes)
    because supperposition of spikes are done here in catalogue in Peeler.
    
    Note:
      * If there are to many peaks, not all of them will have a extracted waveform.
        This why some peak are not labeled (-10) and nb_peak != nb_wveforms
        sometimes.
      * Peaks can belong to diffrents segment, a column indicate it. This is th full list
        of all peaks of all segment.
      * A right click open a ontext menu:
        * move one or several selected spike to trash
        * create a new cluster with one or several spikes
      * When you select one spike, this will auto zoom on **Trace View**,  auto select
        the appriopriate segment and hilight the point on **ND Scatetr**. And vice versa.
    """

    labels_in_table = []

    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        self.label_title = QT.QLabel('')
        self.layout.addWidget(self.label_title)
        
        self.tree = QT.QTreeView(
            minimumWidth = 100, uniformRowHeights = True,
            selectionMode = QT.QAbstractItemView.ExtendedSelection,
            selectionBehavior = QT.QTreeView.SelectRows,
            contextMenuPolicy = QT.Qt.CustomContextMenu,)
        
        self.layout.addWidget(self.tree)
        # self.tree.customContextMenuRequested.connect(self.open_context_menu)
        
        self.model = OnlinePeakModel(controller = controller)
        self.tree.setModel(self.model)
        self.tree.selectionModel().selectionChanged.connect(self.on_tree_selection)

        # This is very slow!!!!!
        #~ for i in range(self.model.columnCount(None)):
            #~ print(i)
            #~ self.tree.resizeColumnToContents(i)
        self.tree.setColumnWidth(0, 120)
        # print('\n'.join(dir(self.tree)))
        # pdb.set_trace()
        
        self.refresh()
    
    def refresh(self):
        self.model.refresh_colors()
        '''
        nb_peak = self.controller.spikes.size
        if self.controller.some_peaks_index is not None:
            nb_sampled = self.controller.some_peaks_index.shape[0]
        else:
            nb_sampled = 0
        self.label_title.setText('<b>All peaks {} - Nb sampled {}</b>'.format(nb_peak, nb_sampled))
        '''
    
    def on_tree_selection(self):
        self.controller.spike_selection[:] = False
        for index in self.tree.selectedIndexes():
            if index.column() == 0:
                ind = self.model.visible_ind[index.row()]
                self.controller.spike_selection[ind] = True
        self.spike_selection_changed.emit()
    
    def on_spike_selection_changed(self):
        self.tree.selectionModel().selectionChanged.disconnect(self.on_tree_selection)
        
        row_selected, = np.nonzero(self.controller.spike_selection[self.model.visible_ind])
        
        if row_selected.size>100:#otherwise this is verry slow
            row_selected = row_selected[:10]
        
        # change selection
        self.tree.selectionModel().clearSelection()
        flags = QT.QItemSelectionModel.Select #| QItemSelectionModel.Rows
        itemsSelection = QT.QItemSelection()
        for r in row_selected:
            for c in range(2):
                index = self.tree.model().index(r,c,QT.QModelIndex())
                ir = QT.QItemSelectionRange( index )
                itemsSelection.append(ir)
        self.tree.selectionModel().select(itemsSelection, flags)

        # set selection visible
        if len(row_selected)>=1:
            index = self.tree.model().index(row_selected[0],0,QT.QModelIndex())
            self.tree.scrollTo(index)

        self.tree.selectionModel().selectionChanged.connect(self.on_tree_selection)        


class OnlineClusterBaseList(WidgetBase):
    """
    Base for ClusterPeakList (catalogue window) and ClusterSpikeList (Peeler window)
    """
    
    sort_by_names = ['label', 'channel', 'amplitude', 'nb_peak']
    labels_in_table = [
        'cluster_label', 'show/hide', 'elecCath', 'elecAno', 'pulseWidth', 'amp', 'freq']

    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)
        
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)
        
        h = QT.QHBoxLayout()
        self.layout.addLayout(h)
        h.addWidget(QT.QLabel('sort by'))
        self.combo_sort = QT.QComboBox()
        self.combo_sort.addItems(self.sort_by_names)
        self.combo_sort.currentIndexChanged.connect(self.refresh)
        h.addWidget(self.combo_sort)
        h.addStretch()
        
        self.table = QT.QTableWidget()
        self.layout.addWidget(self.table)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.cellDoubleClicked.connect(self.on_double_clicked)
        
        self.make_menu()
        
        self.refresh()

    def make_menu(self):
        raise(NotImplementedError)
    
    def refresh(self):
        self.table.itemChanged.disconnect(self.on_item_changed)
        
        self.table.clear()
        labels = [pretty_names.get(label, label) for label in self.labels_in_table]

        self.table.setColumnCount(len(labels))
        self.table.setHorizontalHeaderLabels(labels)
        #~ self.table.setMinimumWidth(100)
        #~ self.table.setColumnWidth(0,60)
        self.table.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        self.table.setSelectionMode(QT.QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QT.QAbstractItemView.SelectRows)
        
        sort_mode = str(self.combo_sort.currentText())
        
        clusters = self.controller.clusters
        clusters = clusters[clusters['cluster_label'] >= 0]
        if sort_mode=='label':
            order =np.arange(clusters.size)
        elif sort_mode=='channel':
            order = np.argsort(clusters['extremum_channel'])
        elif sort_mode=='amplitude':
            order = np.argsort(np.abs(clusters['extremum_amplitude']))[::-1]
        elif sort_mode=='waveform_rms':
            order = np.argsort(clusters['waveform_rms'])[::-1]
        elif sort_mode=='nb_peak':
            order = np.argsort(clusters['nb_peak'])[::-1]
        
        cluster_labels = self._special_label + self.controller.positive_cluster_labels[order].tolist()
        
        self.table.setRowCount(len(cluster_labels))
        
        for i, k in enumerate(cluster_labels):
            color = self.controller.qcolors.get(k, QT.QColor('white'))
            pix = QT.QPixmap(16, 16)
            pix.fill(color)
            icon = QT.QIcon(pix)
            
            if k < 0:
                name = '{} ({})'.format(k, labelcodes.to_name[k])
            else:
                name = '{}'.format(k)

            if 'cluster_label' in self.labels_in_table:
                item_index = self.labels_in_table.index('cluster_label')
                item = QT.QTableWidgetItem(name)
                item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
                self.table.setItem(i, item_index, item)
                item.setIcon(icon)
            
            if 'show/hide' in self.labels_in_table:
                item_index = self.labels_in_table.index('show/hide')
                item = QT.QTableWidgetItem('')
                item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable|QT.Qt.ItemIsUserCheckable)
                
                item.setCheckState(checkboxLookup[self.controller.cluster_visible.get(k, False)])
                self.table.setItem(i, item_index, item)
                item.label = k

            if 'nb_peaks' in self.labels_in_table:
                item_index = self.labels_in_table.index('nb_peaks')
                item = QT.QTableWidgetItem('{}'.format(self.controller.cluster_count.get(k, 0)))
                item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
                self.table.setItem(i, item_index, item)
            
            if 'channel' in self.labels_in_table:
                item_index = self.labels_in_table.index('channel')
                extremum_channel = self.controller.get_extremum_channel(k)
                if extremum_channel is not None:
                    item = QT.QTableWidgetItem('{}: {}'.format(
                        extremum_channel, self.controller.channel_names[extremum_channel]))
                    item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
                    self.table.setItem(i, item_index, item)
            
            if k >= 0:
                clusters = self.controller.clusters
                ## ind = np.searchsorted(clusters['cluster_label'], k) ## wrong because searchsortedmust be ordered
                ind = np.nonzero(clusters['cluster_label'] == k)[0][0]
                
                for item_index, attr in enumerate(self.labels_in_table):
                    if attr in ['cluster_label', 'show/hide', 'nb_peaks', 'channel']:
                        continue
                    value = clusters[attr][ind]
                    if attr in ['elecCath', 'elecAno']:
                        itemLabel = f'{binaryToElecList(value)}'
                    else:
                        itemLabel = f'{value}'
                    item = QT.QTableWidgetItem(itemLabel)
                    item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
                    self.table.setItem(i, item_index, item)

        for i in range(len(self.labels_in_table)):
            self.table.resizeColumnToContents(i)
        self.table.itemChanged.connect(self.on_item_changed)        

    def on_item_changed(self, item):
        if item.column() != 1: return
        sel = {QT.Qt.Unchecked : False, QT.Qt.Checked : True}[item.checkState()]
        #~ k = self.controller.cluster_labels[item.row()]
        k = item.label
        self.controller.cluster_visible[k] = bool(item.checkState())
        self.cluster_visibility_changed.emit()
    
    def on_double_clicked(self, row, col):
        for k in self.controller.cluster_visible:
            self.controller.cluster_visible[k] = False
            
        k = self.table.item(row, 1).label
        self.controller.cluster_visible[k] = True
        self.refresh()
        self.cluster_visibility_changed.emit()
        
    
    def selected_cluster(self):
        selected = []
        #~ for index in self.table.selectedIndexes():
        for item in self.table.selectedItems():
            #~ if index.column() !=1: continue
            if item.column() != 1: continue
            #~ selected.append(self.controller.cluster_labels[index.row()])
            selected.append(item.label)
        return selected
    
    
    def open_context_menu(self):
        self.menu.popup(self.cursor().pos())
        #~ menu.exec_(self.cursor().pos())
    
    def show_all(self):
        for k in self.controller.cluster_visible:
            if k>=0:
                self.controller.cluster_visible[k] = True
        self.refresh()
        self.cluster_visibility_changed.emit()
    
    def hide_all(self):
        for k in self.controller.cluster_visible:
            self.controller.cluster_visible[k] = False
        self.refresh()
        self.cluster_visibility_changed.emit()


class OnlineClusterPeakList(OnlineClusterBaseList):
    """
    **Cluster list** is the central widget for actions for clusters :
    make them visible, merge, trash, sort, split, change color, ...
    
    A context menu with right propose:
      * **Reset colors**
      * **Show all**
      * **Hide all**
      * **Re-label cluster by rms**: this re order cluster so that 0 have the bigger rms
         and N the lowest.
      * **Feature projection with all**: this re compute feature projection (equivalent to left toolbar)
      * **Feature projection with selection**: this re compute feature projection but take
        in account only selected usefull when you have doubt on small cluster and want a specifit
        PCA because variance is absord by big ones.
      * **Move selection to trash**
      * **Merge selection**: re label spikes in the same cluster.
      * **Select on peak list**: a spike  as selected for theses clusters.
      * **Tag selection as same cell**: in case of burst some cell
        can have diffrent waveform shape leading to diferents cluster but
        with same ratio. If you have that do not merge clusters because the
        Peeler wll fail. Prefer tag 2 cluster as same cell.
      * **Split selection**: try to split only selected cluster.
    
    Double click on a row make invisible all others except this one.
    
    Cluster can be visualy ordered by some criteria (rms, amplitude, nb peak, ...)
    This is useless to explore cluster few peaks, or big amplitudes, ...
    
    Negative labels are reserved:
      * -1 is thrash
      * -2 is noise snippet
      * -10 unclassified (because no waveform associated)
      * -9 Alien

    """
    _special_label = [labelcodes.LABEL_UNCLASSIFIED]

    def make_menu(self):
        self.menu = QT.QMenu()

        act = self.menu.addAction('Reset colors')
        act.triggered.connect(self.reset_colors)
        act = self.menu.addAction('Show all')
        act.triggered.connect(self.show_all)
        act = self.menu.addAction('Hide all')
        act.triggered.connect(self.hide_all)
        
        act = self.menu.addAction('Select on peak list')
        act.triggered.connect(self.select_peaks_of_clusters)

        act = self.menu.addAction('Change color/annotation/tag')
        act.triggered.connect(self.change_color_annotation_tag)

    def _selected_spikes(self):
        selection = np.zeros(self.controller.spike_label.shape[0], dtype = bool)
        for k in self.selected_cluster():
            selection |= self.controller.spike_label == k
        return selection
    
    def reset_colors(self):
        self.controller.refresh_colors(reset=True)
        self.refresh()
        self.colors_changed.emit()
    
    def order_clusters(self):
        self.controller.order_clusters()
        self.refresh()
        self.spike_label_changed.emit()

    def select_peaks_of_clusters(self):
        self.controller.spike_selection[:] = self._selected_spikes()
        self.refresh()
        self.spike_selection_changed.emit()
    
    def change_color_annotation_tag(self):
        labels = self.selected_cluster()
        n = len(labels)
        if n!=1: return
        k = labels[0]
        clusters = self.controller.clusters
        ## ind = np.searchsorted(clusters['cluster_label'], k)  ## wrong because searchsortedmust be ordered
        ind = np.nonzero(clusters['cluster_label'] == k)[0][0]
        
        color = QT.QColor(self.controller.qcolors[k])
        annotations = str(clusters[ind]['annotations'])
        tag = str(clusters[ind]['tag'])
        
        params_ = [
            {'name': 'color', 'type': 'color', 'value': color},
            {'name': 'annotations', 'type': 'str', 'value': annotations},
            {'name': 'tag', 'type': 'list', 'value': tag, 'values':gui_params.possible_tags},
        ]        
        
        dia = ParamDialog(params_, title = 'Cluster {}'.format(k), parent=self)
        if dia.exec_():
            d = dia.get()
            self.controller.set_cluster_attributes(k, **d)
            
            self.colors_changed.emit()
            self.refresh()
