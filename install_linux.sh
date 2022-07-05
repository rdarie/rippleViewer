#!/bin/bash

# activate conda
. /opt/conda/etc/profile.d/conda.sh
conda activate
#
conda config --add channels conda-forge
conda config --append channels intel
#
export PYTHONPATH="/home/opt/anaconda3/envs/rippleViewer/lib/python3.8/site-packages"
echo "PYTHONPATH = "$PYTHONPATH
# remove env if exists
# conda remove -n rippleViewer --all --yes # TODO: fails with develop installed packages
rm -rf "/home/opt/anaconda3/envs/rippleViewer"
# clean cached installers from conda
conda clean --all --yes
#
# create environment
conda create -n rippleViewer --file requirements_linux.txt --yes

conda activate rippleViewer
echo "python version: "$(python --version)

echo "Please check if installation was successful. If not, abort by pressing Ctrl-C"
echo "Otherwise, continue by pressing any other key."
read FILLER

QT_PACKAGES=(\
"PySide6-Essentials==6.3.1" \
"PySide6-Addons==6.3.1" \
"shiboken6==6.3.1" \
# "PyQt6==6.3.1" \
# "PyQt6-Qt6==6.3.1" \
# "PyQt6_sip==13.4.0" \
)

for PREREQ in ${QT_PACKAGES[*]}; do
    echo "Installing ${PREREQ} via pip"
    pip install "${PREREQ}" --no-deps --upgrade
done

PIP_PACKAGES=(\
"PyOpenGL-accelerate==3.1.5" \
)

for PREREQ in ${PIP_PACKAGES[*]}; do
    echo "Installing ${PREREQ} via pip"
    pip install "${PREREQ}" --no-deps --upgrade
done

for FILE in ./external_wheels/*.whl; do
    echo "Installing ${FILE}"
    pip install "${FILE}" --no-deps --upgrade
done

GitRepoUser="rdarie"
GitRepoRoot="https://github.com/${GitRepoUser}/"
GitFolder="/home/GitHub"

RepoList=(\
"pyqtgraph" \
"ephyviewer" \
"pyacq" \
"neurotic" \
"tridesclous"
)

RepoOptsList=(\
"" \
" -b rippleViewerV2" \
"" \
"" \
" -b rippleViewer" \
)

cloneRepos=true

if [[ $cloneRepos = true ]]
then
    # make directory for cloned repos
    ENVDIR="/home/rippleViewerEnv"
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
        echo "Deleting contents of "$repoName
        rm -rf $repoName
        #
        echo "Cloning ${GitRepoRoot}${repoName}.git${repoOpts}"
        git clone ${GitRepoRoot}${repoName}.git${repoOpts}
        echo "Installing "$GitRepoRoot$repoName
        # enter this repo
        cd $repoName
        pwd
        python setup.py develop --install-dir=$PYTHONPATH --no-deps
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
        python setup.py develop --no-deps --install-dir=$PYTHONPATH
        cd "${GitFolder}"
    done
fi

cd "${GitFolder}/rippleViewer"

python setup.py develop --install-dir=$PYTHONPATH --no-deps
# python -m pip install --no-warn-conflicts --no-build-isolation --no-deps --editable .

echo "python version: "$(python --version)
conda env config vars set PYQTGRAPH_QT_LIB=PySide6

conda list --explicit > ./conda-spec-file-linux.txt
pip freeze > ./pip-spec-file-linux.txt

pip check

conda env export > ./full-environment-linux.yml
conda env export --from-history > ./short-environment-linux.yml