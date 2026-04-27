# Connect
### Connect to Server
```shell
ssh -i /Users/frederik/.ssh/id_local_machine root@192.168.1.50
```


### Create Tmux Session

#### START SCRAPE
```shell
ssh -i /Users/frederik/.ssh/id_local_machine -t root@192.168.1.50 "tmux new-session -d -s bgg; tmux send-keys -t bgg 'cd /root/bgg-db && python3 main.py' C-m; tmux attach -t bgg"
```


### Connect to Tmux Session
```shell
ssh -i /Users/frederik/.ssh/id_local_machine -t root@192.168.1.50 'tmux attach -t bgg'
```

# Sync
### Push to Linux server
```shell
git add --all && git commit -m "update" && git push
ssh -i /Users/frederik/.ssh/id_local_machine -t root@192.168.1.50 'cd /root/bgg-db; git pull'
```

### Copy data to local machine
```shell
rsync -e "ssh -i /Users/frederik/.ssh/id_local_machine" -avz --progress root@192.168.1.50:/root/bgg-db/data/ /Users/frederik/Home/Python/bgg-db/data
```
```shell
DONTUSE rsync -avz --progress /Users/frederik/Home/Python/bgg-db/data/ root@192.168.1.50:/root/bgg-db/data
```