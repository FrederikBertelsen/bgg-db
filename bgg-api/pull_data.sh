#!/bin/bash
rsync -e "ssh -i /Users/frederik/.ssh/id_local_machine" -avz --progress root@192.168.1.50:/root/bgg-db/downloads/ ./downloads
rsync -e "ssh -i /Users/frederik/.ssh/id_local_machine" -avz --progress root@192.168.1.50:/root/bgg-db/data/ ./data