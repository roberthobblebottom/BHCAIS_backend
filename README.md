notes to self do these for two repo server that pulls with ssh:

root@ubuntu-s-1vcpu-1gb-sgp1:~/BHCAIS_frontend# git config core.sshCommand "ssh -i /root/.ssh/deploy_key_frontend"
Host github.com-bhcais-backend
        Hostname github.com
	User git
        IdentityFile=/root/.ssh/deploy_key

Host github.com-bhcais-frontend
        Hostname github.com
	User git
        IdentityFile=/root/.ssh/deploy_key_frontend
