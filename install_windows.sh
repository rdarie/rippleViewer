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

GitRepoRoot="git://github.com/rdarie/"

RepoList=(\
"pyacq" \
)

cd ..
# clone and install other repos
for repoName in ${RepoList[*]}; do
    # clone the repo
    # echo "Cloning "$GitRepoRoot$repoName".git"
    # git clone $GitRepoRoot$repoName".git"
    
    # enter this repo
    cd $repoName

    # TODO:
    # checkout correct version of the target repo
    # git checkout tags/ndav0.3

    echo "Installing "$GitRepoRoot$repoName
    python setup.py develop --install-dir=$PYTHONPATH --no-deps
    cd ..
done

cd rippleViewer

conda list --explicit > ./conda-spec-file.txt
pip freeze > ./pip-spec-file.txt

pip check