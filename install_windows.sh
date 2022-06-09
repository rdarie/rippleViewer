#!/bin/bash

# activate conda
source ~/.bashrc
conda config --append channels conda-forge
# remove if exists
export PYTHONPATH="${HOME}/.conda/envs/rippleViewer/Lib/site-packages"
conda remove -n rippleViewer --all --yes
rm -rf "${HOME}/.conda/envs/rippleViewer/*"
#
ENVDIR="${HOME}/rippleViewerEnv"
rm -rf $ENVDIR
mkdir $ENVDIR
# create environment
conda create -n rippleViewer --file requirements.txt --yes

echo "Please check if installation was successful. If not, abort by pressing Ctrl-C"
echo "Otherwise, continue by pressing any other key."
read FILLER

conda activate rippleViewer

WHEEL_PREREQS=(\
)

for PREREQ in ${WHEEL_PREREQS[*]}; do
    echo "Installing ${PREREQ} via pip"
    pip install "${PREREQ}" --no-deps --upgrade
done

for FILE in ./wheels/*.whl; do
    echo "Installing ${FILE}"
    pip install "${FILE}" --no-deps --upgrade
done


GitRepoRoot="https://github.com/rdarie/"

RepoList=(\
"pyacq" \
"ephyviewer" \
"neurotic"
)

RepoOptsList=(\
"" \
" -b rippleViewer" \
"" \
)

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
    
    echo "Installing "$GitRepoRoot$repoName
    # enter this repo
    cd $repoName
    pwd
    python setup.py develop --install-dir=$PYTHONPATH --no-deps
    cd $ENVDIR
done

cd rippleViewer

conda list --explicit > ./conda-spec-file.txt
pip freeze > ./pip-spec-file.txt

pip check