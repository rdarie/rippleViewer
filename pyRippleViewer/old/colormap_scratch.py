import seaborn as sns
import pandas as pd
from matplotlib.colors import ListedColormap, to_rgb

flare = sns.color_palette("flare", n_colors=255)
flareSrs = pd.Series(flare)
flareDF = pd.DataFrame(pd.Series(flare).tolist(), columns=['r','g', 'b'])
flareDF.to_csv('flare.csv', header=False, index=False)

crest = sns.color_palette("crest_r", n_colors=255)
crestSrs = pd.Series(crest)
crestDF = pd.DataFrame(pd.Series(crest).tolist(), columns=['r','g', 'b'])
crestDF.to_csv('crest_r.csv', header=False, index=False)

tol_vibrant = ListedColormap(["#ee7733", "#0077bb", "#33bbee", "#ee3377", "#cc3311", "#009988", "#bbbbbb"], name='tol_vibrant')
tol_vibrantDF = pd.DataFrame(pd.Series(tol_vibrant.colors).apply(to_rgb).tolist(), columns=['r','g', 'b'])
tol_vibrantDF.to_csv('tol_vibrant.csv', header=False, index=False)
sns.palplot(sns.color_palette(tol_vibrant.colors))