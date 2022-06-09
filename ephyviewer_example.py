import ephyviewer
import numpy as np
from pyacq.viewers import TraceViewer

app = ephyviewer.mkQApp()

#signals
sigs = np.random.rand(100000,16)
sample_rate = 1000.
t_start = 0.
view1 = TraceViewer.from_numpy(sigs, sample_rate, t_start, 'Signals')

win = ephyviewer.MainViewer(debug=True, show_auto_scale=True, show_play=False)
win.add_view(view1)
win.show()

app.exec_()