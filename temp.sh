export ANACONDA_ROOT='/C/Users/CINNR/.conda'
. "/C/ProgramData/Anaconda3/etc/profile.d/conda.sh"

export ENV_DIR="${ANACONDA_ROOT}/envs/rippleViewer"

GitRepoRoot="https://github.com/rdarie/"
GitFolder="${HOME}/Documents/GitHub/rdarie"

conda activate rippleViewer

RepoList=(\
"pyqtgraph" \
"ephyviewer" \
"ISI_Vicon_DataStream_MOCK" \
"pyacq" \
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
    CUSTOMDIR="${HOME}/rippleViewerEnv"
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
        # pip install --no-warn-conflicts --no-build-isolation --no-deps --editable "${GitFolder}/${repoName}"
        cd $CUSTOMDIR
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

viconSDKPath="/c/Program Files/Vicon/DataStream SDK/Win64/Python/vicon_dssdk"
cd "${viconSDKPath}"
python setup.py develop --install-dir=$PYTHONPATH --no-deps

cd "${GitFolder}/rippleViewer"

python setup.py develop --install-dir=$PYTHONPATH --no-deps
# python -m pip install --no-warn-conflicts --no-build-isolation --no-deps --editable .

echo "python version: "$(python --version)

conda list --explicit > ./conda-spec-file-win.txt
pip freeze > ./pip-spec-file-win.txt

conda env export > ./full-environment-win.yml
conda env export --from-history > ./short-environment-win.yml