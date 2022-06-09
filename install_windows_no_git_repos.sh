#!/bin/bash

# activate conda
source ~/.bashrc
conda config --append channels conda-forge

# remove if exists
export PYTHONPATH="${HOME}/.conda/envs/rippleViewer/Lib/site-packages"
conda remove -n rippleViewer --all --yes
rm -rf "${HOME}/.conda/envs/rippleViewer/*"

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

RepoList=(\
"${HOME}/Documents/GitHub/ephyviewer" \
"${HOME}/Documents/GitHub/pyacq" \
"${HOME}/Documents/GitHub/neurotic" \
)

# Install other repos
for i in ${!RepoList[@]}; do
    echo $i
    repoName=${RepoList[i]}
    echo "Installing: ${repoName}"
    #
    # enter this repo
    cd $repoName
    python setup.py develop --install-dir=$PYTHONPATH --no-deps
done

cd "${HOME}/Documents/GitHub/rippleViewer"

conda list --explicit > ./conda-spec-file.txt
pip freeze > ./pip-spec-file.txt

pip check