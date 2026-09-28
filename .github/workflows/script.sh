echo "INSIDE THE SERVER VIA SSH" 
cd ${{ secrets.APP_DIR }} 
GIT_SSH_COMMAND='ssh -i ~/.ssh/github_action_git_pull_key -o IdentitiesOnly=yes' 
git pull https://github.com/roberthobblebottom/BHCAIS_backend.git"