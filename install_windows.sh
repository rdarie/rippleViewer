#!/bin/bash

# activate conda
export ANACONDA_ROOT='/c/anaconda3'
. "${ANACONDA_ROOT}/etc/profile.d"/conda.sh

export GitRepoRoot="https://github.com/rdarie/"
export GitFolder="${HOME}/Documents/GitHub"
export ENV_DIR="${ANACONDA_ROOT}/envs/ripple_viewer_env"

conda activate
conda config --set pip_interop_enabled True
conda config --append channels conda-forge
# conda config --append channels intel

# remove env if exists
# conda remove -n ripple_viewer_env --all --yes # TODO: fails with develop installed packages
rm -rf "${ENV_DIR}"

# clean cached installers from conda
conda clean --all --yes

# create environment
echo "Creating conda environment"
conda create -n ripple_viewer_env --file requirements_win.txt --yes
conda activate ripple_viewer_env
conda env config vars set PYQTGRAPH_QT_LIB=PySide6
conda env config vars set PYTHONPATH="${ENV_DIR}/Lib/site-packages"
conda deactivate
conda activate ripple_viewer_env

echo "python version: "$(python --version)
echo PYTHONPATH=$PYTHONPATH
echo "Please check if installation was successful. If not, abort by pressing Ctrl-C"
echo "Otherwise, continue by pressing any other key."
read FILLER

QT_PACKAGES=(\
"PySide6==6.3.1" \
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

for FILE in ./external_wheels/windows/*.whl; do
    echo "Installing ${FILE}"
    python -m pip install "${FILE}" --no-build-isolation --upgrade --no-cache-dir
done

RepoList=(\
"pyqtgraph" \
"ephyviewer" \
"pyacq" \
"ISI_Vicon_DataStream_MOCK" \
)

RepoOptsList=(\
"" \
" -b rippleViewerV2" \
"" \
"" \
)

cloneRepos=false

if [[ $cloneRepos = true ]]
then
    # make directory for cloned repos
    CUSTOMDIR="${HOME}/ripple_viewer_repos"
    rm -rf $CUSTOMDIR
    mkdir $CUSTOMDIR
    cd $CUSTOMDIR
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
        python setup.py develop --install-dir=$PYTHONPATH --no-deps
        cd $CUSTOMDIR
    done
else
    # Install other repos
    for i in ${!RepoList[@]}; do
        repoName=${RepoList[i]}
        echo "Installing: ${GitFolder}/${repoName}"
        cd "${GitFolder}/${repoName}"
        python setup.py develop --no-deps --install-dir=$PYTHONPATH
        cd "${GitFolder}"
    done
fi

# viconSDKPath="/c/Program Files/Vicon/DataStream SDK/Win64/Python/vicon_dssdk"
# cd "${viconSDKPath}"
# python setup.py develop --install-dir=$PYTHONPATH --no-deps

cd "${GitFolder}/rippleViewer"
python setup.py develop --install-dir=$PYTHONPATH --no-deps

echo "python version: "$(python --version)
conda list --explicit > ./conda-spec-file-win.txt
pip freeze > ./pip-spec-file-win.txt
conda env export > ./full-environment-win.yml
conda env export --from-history > ./short-environment-win.yml
