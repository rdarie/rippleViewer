#!/bin/bash

# activate conda
source ~/.bashrc
conda activate

conda config --set pip_interop_enabled True
conda config --append channels conda-forge
conda config --append channels intel

export ANACONDA_ROOT="/C/Users/Radu/anaconda3"
export SITE_PACKAGES_DIR="${ANACONDA_ROOT}/envs/rippleViewer/Lib/site-packages"
echo SITE_PACKAGES_DIR=$SITE_PACKAGES_DIR

# remove env if exists
# conda remove -n rippleViewer --all --yes # TODO: fails with develop installed packages
rm -rf "${ANACONDA_ROOT}/envs/rippleViewer"

# clean cached installers from conda
conda clean --all --yes
#
# create environment
echo "Creating conda environment"
conda create -n rippleViewer --file requirements_win.txt --yes

conda activate rippleViewer

conda env config vars set PYQTGRAPH_QT_LIB=PySide6
export PYQTGRAPH_QT_LIB=PySide6

echo "python version: "$(python --version)

echo "Please check if installation was successful. If not, abort by pressing Ctrl-C"
echo "Otherwise, continue by pressing any other key."
read FILLER

QT_PACKAGES=(\
# "shiboken6==6.3.1" \
"PySide6==6.3.1" \
# "PySide6-Essentials==6.3.1" \
# "PySide6-Addons==6.3.1" \
)

for PREREQ in ${QT_PACKAGES[*]}; do
    echo "Installing ${PREREQ} via pip"
    python -m pip install "${PREREQ}" --no-build-isolation --upgrade --no-cache-dir
done

PIP_PACKAGES=(\
"PyOpenGL-accelerate==3.1.6" \
)

for PREREQ in ${PIP_PACKAGES[*]}; do
    echo "Installing ${PREREQ} via pip"
    python -m pip install "${PREREQ}" --no-build-isolation --upgrade --no-cache-dir
done

for FILE in ./external_wheels/*.whl; do
    echo "Installing ${FILE}"
    python -m pip install "${FILE}" --no-build-isolation --upgrade --no-cache-dir
done

GitRepoRoot="https://github.com/rdarie/"
GitFolder="${HOME}/Documents/GitHub"

RepoList=(\
"pyqtgraph" \
"ephyviewer" \
"tridesclous"
"pyacq" \
"neurotic" \
)

RepoOptsList=(\
"" \
" -b rippleViewerV2" \
" -b rippleViewer" \
"" \
"" \
)

cloneRepos=false

if [[ $cloneRepos = true ]]
then
    # make directory for cloned repos
    ENVDIR="${HOME}/rippleViewerEnv"
    rm -rf $ENVDIR
    mkdir $ENVDIR
    cd $ENVDIR
    # clone and install other repos
    for i in ${!RepoList[@]}; do
        echo $i
        # clone the repo
        repoOpts=${RepoOptsList[i]}
        echo "repoOpts =${repoOpts}"
        repoName=${RepoList[i]}
        echo "repoName =${repoName}"
        #
        echo "Cloning ${GitRepoRoot}${repoName}.git${repoOpts}"
        eval "git clone ${GitRepoRoot}${repoName}.git${repoOpts}"
        #
        echo "Installing "$GitRepoRoot$repoName
        # enter this repo
        cd $repoName
        # pwd
        python setup.py develop --install-dir=$SITE_PACKAGES_DIR --no-deps
        # pip install --no-warn-conflicts --no-build-isolation --no-deps --editable "${GitFolder}/${repoName}"
        cd $ENVDIR
    done
else
    # Install other repos
    for i in ${!RepoList[@]}; do
        echo $i
        repoName=${RepoList[i]}
        echo "Installing: ${GitFolder}/${repoName}"
        cd "${GitFolder}/${repoName}"
        pwd
        # python -m pip install --no-warn-conflicts --no-build-isolation --no-deps --editable "${GitFolder}/${repoName}"
        python setup.py develop --no-deps --install-dir=$SITE_PACKAGES_DIR
        cd "${GitFolder}"
    done
fi

cd "${GitFolder}/rippleViewer"

python setup.py develop --install-dir=$SITE_PACKAGES_DIR --no-deps
# python -m pip install --no-warn-conflicts --no-build-isolation --no-deps --editable .

echo "python version: "$(python --version)

conda list --explicit > ./conda-spec-file-win.txt
pip freeze > ./pip-spec-file-win.txt

conda env export > ./full-environment-win.yml
conda env export --from-history > ./short-environment-win.yml